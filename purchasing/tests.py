from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User
from billing.models import TypeFrais
from partners.models import Partner, PartnerType
from treasury.models import CashAccount, TypeMouvement

from .forms import SupplierInvoiceForm
from .models import StatutAchat, SupplierInvoice, SupplierInvoiceLine, SupplierPayment


class SupplierInvoiceTotalsTests(TestCase):
    def setUp(self):
        self.fournisseur = Partner.objects.create(
            type_tiers=PartnerType.FOURNISSEUR, raison_sociale="Maersk Line"
        )
        self.invoice = SupplierInvoice.objects.create(fournisseur=self.fournisseur)

    def test_montant_total_sums_lines(self):
        SupplierInvoiceLine.objects.create(
            invoice=self.invoice, type_frais=TypeFrais.TRANSPORT, designation="Fret",
            quantite=1, prix_unitaire=Decimal("45000"),
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
            quantite=1, prix_unitaire=Decimal("45000"),
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
