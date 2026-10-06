from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User
from dossiers.models import Dossier, TypeOperation
from partners.models import Partner, PartnerType
from treasury.models import CashAccount, TypeMouvement

from .models import Invoice, InvoiceLine, Payment, StatutFacture, TypeFrais


class InvoiceTotalsTests(TestCase):
    def setUp(self):
        self.client_partner = Partner.objects.create(
            type_tiers=PartnerType.CLIENT, raison_sociale="Atlas Industries"
        )
        self.invoice = Invoice.objects.create(client=self.client_partner)

    def test_montant_total_sums_lines(self):
        InvoiceLine.objects.create(
            invoice=self.invoice, type_frais=TypeFrais.HONORAIRES, designation="Honoraires",
            quantite=1, prix_unitaire=Decimal("3500"),
        )
        InvoiceLine.objects.create(
            invoice=self.invoice, type_frais=TypeFrais.ACCONAGE, designation="Acconage",
            quantite=2, prix_unitaire=Decimal("600"),
        )
        self.assertEqual(self.invoice.montant_total, Decimal("4700"))

    def test_solde_accounts_for_payments(self):
        InvoiceLine.objects.create(
            invoice=self.invoice, type_frais=TypeFrais.HONORAIRES, designation="Honoraires",
            quantite=1, prix_unitaire=Decimal("5000"),
        )
        Payment.objects.create(invoice=self.invoice, montant=Decimal("2000"), date_paiement="2026-01-01")
        self.assertEqual(self.invoice.montant_paye, Decimal("2000"))
        self.assertEqual(self.invoice.solde, Decimal("3000"))
        self.assertTrue(self.invoice.is_impayee)

    def test_fully_paid_invoice_is_not_impayee(self):
        InvoiceLine.objects.create(
            invoice=self.invoice, type_frais=TypeFrais.HONORAIRES, designation="Honoraires",
            quantite=1, prix_unitaire=Decimal("1000"),
        )
        Payment.objects.create(invoice=self.invoice, montant=Decimal("1000"), date_paiement="2026-01-01")
        self.assertEqual(self.invoice.solde, Decimal("0"))
        self.assertFalse(self.invoice.is_impayee)


class PaymentCreateViewTests(TestCase):
    def setUp(self):
        self.comptable = User.objects.create_user(
            username="compta", password="pass12345", role=Role.COMPTABLE
        )
        self.agent = User.objects.create_user(
            username="agent", password="pass12345", role=Role.AGENT_TRANSIT
        )
        self.client_partner = Partner.objects.create(
            type_tiers=PartnerType.CLIENT, raison_sociale="Atlas Industries"
        )
        self.invoice = Invoice.objects.create(client=self.client_partner)
        InvoiceLine.objects.create(
            invoice=self.invoice, type_frais=TypeFrais.HONORAIRES, designation="Honoraires",
            quantite=1, prix_unitaire=Decimal("5000"),
        )
        self.compte = CashAccount.objects.create(nom="Compte principal", solde_initial=Decimal("0"))

    def test_agent_without_billing_role_cannot_record_payment(self):
        self.client.login(username="agent", password="pass12345")
        response = self.client.post(
            reverse("billing:payment_create", kwargs={"invoice_pk": self.invoice.pk}),
            {"montant": "1000", "date_paiement": "2026-01-01", "mode_paiement": "virement"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Payment.objects.exists())

    def test_comptable_can_record_payment(self):
        self.client.login(username="compta", password="pass12345")
        response = self.client.post(
            reverse("billing:payment_create", kwargs={"invoice_pk": self.invoice.pk}),
            {"montant": "2000", "date_paiement": "2026-01-01", "mode_paiement": "virement"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Payment.objects.count(), 1)

    def test_payment_linked_to_cash_account_creates_matching_treasury_entry(self):
        self.client.login(username="compta", password="pass12345")
        self.client.post(
            reverse("billing:payment_create", kwargs={"invoice_pk": self.invoice.pk}),
            {
                "montant": "2000", "date_paiement": "2026-01-01", "mode_paiement": "virement",
                "compte": self.compte.pk,
            },
        )
        self.compte.refresh_from_db()
        self.assertEqual(self.compte.solde, Decimal("2000"))
        movement = self.compte.mouvements.get()
        self.assertEqual(movement.type_mouvement, TypeMouvement.ENTREE)
        self.assertEqual(movement.related_payment.invoice, self.invoice)

    def test_partial_payment_sets_statut_payee_partiel(self):
        self.client.login(username="compta", password="pass12345")
        self.client.post(
            reverse("billing:payment_create", kwargs={"invoice_pk": self.invoice.pk}),
            {"montant": "1000", "date_paiement": "2026-01-01", "mode_paiement": "virement"},
        )
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.statut, StatutFacture.PAYEE_PARTIEL)

    def test_full_payment_sets_statut_payee(self):
        self.client.login(username="compta", password="pass12345")
        self.client.post(
            reverse("billing:payment_create", kwargs={"invoice_pk": self.invoice.pk}),
            {"montant": "5000", "date_paiement": "2026-01-01", "mode_paiement": "virement"},
        )
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.statut, StatutFacture.PAYEE)
