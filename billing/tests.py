import datetime
from decimal import Decimal
from io import BytesIO

from django.test import TestCase
from django.urls import reverse
from pypdf import PdfReader

from accounts.models import Role, User
from core.models import Societe
from dossiers.models import Dossier, TypeOperation
from partners.models import Partner

from .models import (
    TAUX_TVA_PAR_FRAIS, Invoice, InvoiceLine, Payment, Quote, QuoteLine, TypeDevis, TypeFrais,
)


def pdf_text(content):
    return "\n".join(page.extract_text() for page in PdfReader(BytesIO(content)).pages)


class TvaTests(TestCase):
    def setUp(self):
        self.partner = Partner.objects.create(raison_sociale="Atlas Import")

    def test_totals_per_rate(self):
        invoice = Invoice.objects.create(client=self.partner)
        for type_frais, qte, pu, taux in (
            ("honoraires", "1", "1000.00", 20),
            ("manutention", "3", "33.33", 20),   # 99.99 HT
            ("transport", "1", "500.00", 14),
            ("debours", "1", "2000.00", 0),
        ):
            InvoiceLine.objects.create(
                invoice=invoice, type_frais=type_frais, designation=type_frais,
                quantite=qte, prix_unitaire=pu, taux_tva=taux,
            )
        self.assertEqual(invoice.montant_ht, Decimal("3599.99"))
        self.assertEqual(invoice.ventilation_tva, [
            {"taux": 0, "base": Decimal("2000.00"), "tva": Decimal("0.00")},
            {"taux": 14, "base": Decimal("500.00"), "tva": Decimal("70.00")},
            {"taux": 20, "base": Decimal("1099.99"), "tva": Decimal("220.00")},
        ])
        self.assertEqual(invoice.montant_tva, Decimal("290.00"))
        self.assertEqual(invoice.montant_total, Decimal("3889.99"))

        Payment.objects.create(invoice=invoice, montant="1000", date_paiement=datetime.date(2026, 10, 6))
        self.assertEqual(invoice.solde, Decimal("2889.99"))

    def test_new_lines_default_to_20_percent(self):
        quote = Quote.objects.create(client=self.partner)
        line = QuoteLine.objects.create(quote=quote, type_frais="honoraires", designation="x", prix_unitaire="10")
        self.assertEqual(line.taux_tva, 20)
        self.assertEqual(line.montant_ttc, Decimal("12.00"))

    def test_default_rate_by_fee_type(self):
        self.assertEqual(TAUX_TVA_PAR_FRAIS[TypeFrais.DEBOURS], 0)
        self.assertEqual(TAUX_TVA_PAR_FRAIS[TypeFrais.DROITS_TAXES], 0)
        self.assertEqual(TAUX_TVA_PAR_FRAIS[TypeFrais.TRANSPORT], 14)
        self.assertEqual(TAUX_TVA_PAR_FRAIS[TypeFrais.HONORAIRES], 20)
        self.assertEqual(set(TAUX_TVA_PAR_FRAIS), set(TypeFrais.values))

    def test_invoice_form_saves_rate(self):
        user = User.objects.create_user("compta", password="x", role=Role.COMPTABLE)
        self.client.force_login(user)
        resp = self.client.post(reverse("billing:invoice_create"), {
            "client": self.partner.pk, "statut": "brouillon",
            "lignes-TOTAL_FORMS": "1", "lignes-INITIAL_FORMS": "0",
            "lignes-MIN_NUM_FORMS": "0", "lignes-MAX_NUM_FORMS": "1000",
            "lignes-0-type_frais": "transport", "lignes-0-designation": "Transport",
            "lignes-0-quantite": "1", "lignes-0-prix_unitaire": "100", "lignes-0-taux_tva": "14",
        })
        invoice = Invoice.objects.get()
        self.assertRedirects(resp, invoice.get_absolute_url())
        self.assertEqual(invoice.montant_total, Decimal("114.00"))
        page = self.client.get(invoice.get_absolute_url())
        self.assertContains(page, "TVA 14 %")
        self.assertContains(page, "Total TTC")

    def test_form_page_exposes_default_rates(self):
        self.client.force_login(User.objects.create_user("agent", password="x"))
        resp = self.client.get(reverse("billing:quote_create"))
        self.assertContains(resp, 'id="taux-par-frais"')
        self.assertContains(resp, '"debours": 0')


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
            invoice=invoice, type_frais="honoraires", designation="Honoraires", prix_unitaire="1250.50",
            taux_tva=20,
        )
        InvoiceLine.objects.create(
            invoice=invoice, type_frais="droits_taxes", designation="Droits de douane", prix_unitaire="300",
            taux_tva=0,
        )
        Payment.objects.create(invoice=invoice, montant="250.50", date_paiement=datetime.date(2026, 10, 6))

        resp = self.client.get(reverse("billing:invoice_pdf", args=[invoice.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertEqual(resp["Content-Disposition"], f'inline; filename="{invoice.reference}.pdf"')
        text = pdf_text(resp.content)
        for expected in (
            invoice.reference, self.dossier.reference, "Atlas Import", "001234567000089",
            # HT 1 550,50 ; TVA 20 % sur 1 250,50 = 250,10 ; TTC 1 800,60 ; reste 1 550,10
            "1 550,50", "250,10", "1 800,60", "Reste", "1 550,10", "VENTILATION TVA", "Exonéré/débours",
            "Mille huit cents dirhams et soixante centimes",
        ):
            self.assertIn(expected, text)

    def test_quote_pdf_download(self):
        quote = Quote.objects.create(client=self.partner, type_devis=TypeDevis.PROFORMA)
        QuoteLine.objects.create(
            quote=quote, type_frais="transport", designation="Transport", prix_unitaire="3000", taux_tva=0
        )

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
