import datetime
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User
from billing.models import TypeFrais
from partners.models import Partner, PartnerType
from treasury.models import CashAccount, TypeMouvement

from .forms import SupplierInvoiceForm
from .models import (
    TAUX_TVA_ACHAT_PAR_FRAIS, StatutAchat, SupplierInvoice, SupplierInvoiceLine, SupplierPayment,
)


class SupplierVatTests(TestCase):
    def setUp(self):
        self.fournisseur = Partner.objects.create(raison_sociale="Port Services", type_tiers="prestataire")
        self.client.force_login(User.objects.create_user("compta", password="x", role=Role.COMPTABLE))

    def test_totals_and_balance_are_ttc(self):
        achat = SupplierInvoice.objects.create(fournisseur=self.fournisseur, statut=StatutAchat.VALIDEE)
        for type_frais, pu, taux in (("debours", "1000", 20), ("transport", "500", 14), ("droits_taxes", "3000", 0)):
            SupplierInvoiceLine.objects.create(
                invoice=achat, type_frais=type_frais, designation=type_frais, prix_unitaire=pu, taux_tva=taux
            )
        self.assertEqual(achat.montant_ht, Decimal("4500.00"))
        self.assertEqual(achat.montant_tva, Decimal("270.00"))
        self.assertEqual(achat.montant_total, Decimal("4770.00"))
        SupplierPayment.objects.create(invoice=achat, montant="770", date_paiement=datetime.date(2026, 10, 6))
        self.assertEqual(achat.solde, Decimal("4000.00"))

    def test_purchase_default_rates(self):
        self.assertEqual(TAUX_TVA_ACHAT_PAR_FRAIS[TypeFrais.DEBOURS], 20)  # unlike sales
        self.assertEqual(TAUX_TVA_ACHAT_PAR_FRAIS[TypeFrais.DROITS_TAXES], 0)
        self.assertEqual(TAUX_TVA_ACHAT_PAR_FRAIS[TypeFrais.TRANSPORT], 14)
        self.assertEqual(set(TAUX_TVA_ACHAT_PAR_FRAIS), set(TypeFrais.values))

    def test_client_exemption_never_applies_to_purchases(self):
        self.fournisseur.exonere_tva = True
        self.fournisseur.motif_exoneration = "Zone franche"
        self.fournisseur.save()
        achat = SupplierInvoice.objects.create(fournisseur=self.fournisseur)
        line = SupplierInvoiceLine.objects.create(
            invoice=achat, type_frais="debours", designation="x", prix_unitaire="100", taux_tva=20
        )
        self.assertEqual(line.taux_tva, 20)

    def test_form_and_detail(self):
        resp = self.client.get(reverse("purchasing:invoice_create"))
        self.assertContains(resp, '"debours": 20')
        self.assertContains(resp, 'id="clients-exoneres"')

        resp = self.client.post(reverse("purchasing:invoice_create"), {
            "fournisseur": self.fournisseur.pk, "statut": "brouillon", "date_facture": "2026-10-06",
            "lignes-TOTAL_FORMS": "1", "lignes-INITIAL_FORMS": "0",
            "lignes-MIN_NUM_FORMS": "0", "lignes-MAX_NUM_FORMS": "1000",
            "lignes-0-type_frais": "transport", "lignes-0-designation": "Camion",
            "lignes-0-quantite": "1", "lignes-0-prix_unitaire": "1000", "lignes-0-taux_tva": "14",
        }, follow=True)
        achat = SupplierInvoice.objects.get()
        self.assertEqual(achat.montant_total, Decimal("1140.00"))
        self.assertContains(resp, "TVA 14 %")
        self.assertContains(resp, "Total TTC")


class SupplierInvoiceTotalsTests(TestCase):
    """Non-VAT sanity checks: taux_tva is pinned to 0 so HT == TTC (VAT math covered above)."""

    def setUp(self):
        self.fournisseur = Partner.objects.create(
            type_tiers=PartnerType.FOURNISSEUR, raison_sociale="Maersk Line"
        )
        self.invoice = SupplierInvoice.objects.create(fournisseur=self.fournisseur)

    def test_montant_total_sums_lines(self):
        SupplierInvoiceLine.objects.create(
            invoice=self.invoice, type_frais=TypeFrais.TRANSPORT, designation="Fret",
            quantite=1, prix_unitaire=Decimal("45000"), taux_tva=0,
        )
        self.assertEqual(self.invoice.montant_total, Decimal("45000"))

    def test_reference_is_auto_generated_with_ac_prefix(self):
        self.assertTrue(self.invoice.reference.startswith("AC-"))


class SupplierInvoiceFormClientFilterTests(TestCase):
    def test_only_supplier_type_partners_are_selectable(self):
        client_partner = Partner.objects.create(
            type_tiers=PartnerType.CLIENT, raison_sociale="Atlas Industries"
        )
        fournisseur = Partner.objects.create(
            type_tiers=PartnerType.FOURNISSEUR, raison_sociale="Maersk Line"
        )
        form = SupplierInvoiceForm()
        queryset = form.fields["fournisseur"].queryset
        self.assertIn(fournisseur, queryset)
        self.assertNotIn(client_partner, queryset)


class SupplierPaymentCreateViewTests(TestCase):
    def setUp(self):
        self.comptable = User.objects.create_user(
            username="compta", password="pass12345", role=Role.COMPTABLE
        )
        self.agent = User.objects.create_user(
            username="agent", password="pass12345", role=Role.AGENT_TRANSIT
        )
        self.fournisseur = Partner.objects.create(
            type_tiers=PartnerType.FOURNISSEUR, raison_sociale="Maersk Line"
        )
        self.invoice = SupplierInvoice.objects.create(fournisseur=self.fournisseur)
        SupplierInvoiceLine.objects.create(
            invoice=self.invoice, type_frais=TypeFrais.TRANSPORT, designation="Fret",
            quantite=1, prix_unitaire=Decimal("45000"), taux_tva=0,
        )
        self.compte = CashAccount.objects.create(
            nom="Compte principal", solde_initial=Decimal("50000")
        )

    def test_agent_without_billing_role_cannot_record_payment(self):
        self.client.login(username="agent", password="pass12345")
        response = self.client.post(
            reverse("purchasing:payment_create", kwargs={"invoice_pk": self.invoice.pk}),
            {"montant": "45000", "date_paiement": "2026-01-01", "mode_paiement": "virement"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SupplierPayment.objects.exists())

    def test_full_payment_debits_cash_account_and_marks_paid(self):
        self.client.login(username="compta", password="pass12345")
        response = self.client.post(
            reverse("purchasing:payment_create", kwargs={"invoice_pk": self.invoice.pk}),
            {
                "montant": "45000", "date_paiement": "2026-01-01", "mode_paiement": "virement",
                "compte": self.compte.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.compte.refresh_from_db()
        self.assertEqual(self.compte.solde, Decimal("5000"))
        movement = self.compte.mouvements.get()
        self.assertEqual(movement.type_mouvement, TypeMouvement.SORTIE)
        self.assertEqual(movement.related_supplier_payment.invoice, self.invoice)

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.statut, StatutAchat.PAYEE)
