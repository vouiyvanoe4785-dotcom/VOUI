import datetime
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User
from billing.models import TypeFrais
from partners.models import Partner

from .models import TAUX_TVA_ACHAT_PAR_FRAIS, StatutAchat, SupplierInvoice, SupplierInvoiceLine, SupplierPayment


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
