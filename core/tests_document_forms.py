from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User
from billing.models import Invoice, InvoiceLine, Quote
from partners.models import Partner
from purchasing.models import SupplierInvoice

MGMT = {
    "lignes-TOTAL_FORMS": "1", "lignes-INITIAL_FORMS": "0",
    "lignes-MIN_NUM_FORMS": "0", "lignes-MAX_NUM_FORMS": "1000",
}
# A line with an amount but no designation: the line form is invalid.
LIGNE_INVALIDE = {
    "lignes-0-type_frais": "honoraires", "lignes-0-designation": "",
    "lignes-0-quantite": "1", "lignes-0-prix_unitaire": "100", "lignes-0-taux_tva": "20",
}
LIGNE_VALIDE = {**LIGNE_INVALIDE, "lignes-0-designation": "Honoraires"}


class DocumentWithLinesSaveTests(TestCase):
    """A document and its lines are saved together, or not at all."""

    def setUp(self):
        self.client.force_login(User.objects.create_user("compta", password="x", role=Role.COMPTABLE))
        self.partner = Partner.objects.create(raison_sociale="ACME")
        self.fournisseur = Partner.objects.create(raison_sociale="Transports Sud", type_tiers="transporteur")

    def cases(self):
        yield Invoice, reverse("billing:invoice_create"), {"client": self.partner.pk, "statut": "brouillon"}
        yield Quote, reverse("billing:quote_create"), {
            "client": self.partner.pk, "statut": "brouillon", "type_devis": "devis",
        }
        yield SupplierInvoice, reverse("purchasing:invoice_create"), {
            "fournisseur": self.fournisseur.pk, "statut": "brouillon", "date_facture": "2026-10-06",
        }

    def test_invalid_line_saves_nothing_then_valid_resubmit_creates_one(self):
        for model, url, header in self.cases():
            with self.subTest(model=model.__name__):
                resp = self.client.post(url, {**header, **MGMT, **LIGNE_INVALIDE})
                self.assertEqual(resp.status_code, 200)
                self.assertTrue(resp.context["formset"].errors[0])
                self.assertEqual(model.objects.count(), 0)

                resp = self.client.post(url, {**header, **MGMT, **LIGNE_VALIDE})
                self.assertEqual(resp.status_code, 302)
                self.assertEqual(model.objects.count(), 1)
                self.assertEqual(model.objects.get().lignes.count(), 1)

    def test_invalid_line_on_edit_keeps_header_unchanged(self):
        invoice = Invoice.objects.create(client=self.partner, notes="avant")
        InvoiceLine.objects.create(invoice=invoice, type_frais="honoraires", designation="H", prix_unitaire="10")
        resp = self.client.post(reverse("billing:invoice_update", args=[invoice.pk]), {
            "client": self.partner.pk, "statut": "brouillon", "notes": "après",
            **MGMT, **LIGNE_INVALIDE,
        })
        self.assertEqual(resp.status_code, 200)
        invoice.refresh_from_db()
        self.assertEqual(invoice.notes, "avant")
