import datetime
from io import BytesIO

from django.test import TestCase
from django.urls import reverse
from pypdf import PdfReader

from accounts.models import Role, User
from core.models import Societe
from dossiers.models import Dossier, TypeOperation
from partners.models import Partner

from .models import Invoice, InvoiceLine, Payment, Quote, QuoteLine, TypeDevis


def pdf_text(content):
    return "\n".join(page.extract_text() for page in PdfReader(BytesIO(content)).pages)


class BillingPdfTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("agent", password="x", role=Role.AGENT_TRANSIT)
        self.client.force_login(self.user)
        societe = Societe.load()
        societe.raison_sociale = "Ayden Transit SARL"
        societe.ice = "001234567000089"
        societe.save()
        self.partner = Partner.objects.create(raison_sociale="Atlas Import", ice="0022")
        self.dossier = Dossier.objects.create(client=self.partner, type_operation=TypeOperation.IMPORT)

    def test_invoice_pdf(self):
        invoice = Invoice.objects.create(
            client=self.partner, dossier=self.dossier, date_echeance=datetime.date(2026, 11, 5)
        )
        InvoiceLine.objects.create(
            invoice=invoice, type_frais="honoraires", designation="Honoraires", prix_unitaire="1250.50"
        )
        Payment.objects.create(invoice=invoice, montant="250.50", date_paiement=datetime.date(2026, 10, 6))

        resp = self.client.get(reverse("billing:invoice_pdf", args=[invoice.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertEqual(resp["Content-Disposition"], f'inline; filename="{invoice.reference}.pdf"')
        text = pdf_text(resp.content)
        for expected in (
            invoice.reference, self.dossier.reference, "Atlas Import", "001234567000089",
            "Reste", "1 000,00",
        ):
            self.assertIn(expected, text)

    def test_quote_pdf_download(self):
        quote = Quote.objects.create(client=self.partner, type_devis=TypeDevis.PROFORMA)
        QuoteLine.objects.create(quote=quote, type_frais="transport", designation="Transport", prix_unitaire="3000")

        resp = self.client.get(reverse("billing:quote_pdf", args=[quote.pk]) + "?download=1")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Disposition"], f'attachment; filename="{quote.reference}.pdf"')
        text = pdf_text(resp.content)
        self.assertIn("PROFORMA", text)
        self.assertIn("Trois mille dirhams", text)
        self.assertNotIn("Reste", text)

    def test_pdf_requires_login(self):
        quote = Quote.objects.create(client=self.partner)
        self.client.logout()
        resp = self.client.get(reverse("billing:quote_pdf", args=[quote.pk]))
        self.assertEqual(resp.status_code, 302)

    def test_detail_pages_link_to_pdf(self):
        invoice = Invoice.objects.create(client=self.partner)
        quote = Quote.objects.create(client=self.partner)
        self.assertContains(
            self.client.get(invoice.get_absolute_url()), reverse("billing:invoice_pdf", args=[invoice.pk])
        )
        self.assertContains(
            self.client.get(quote.get_absolute_url()), reverse("billing:quote_pdf", args=[quote.pk])
        )
