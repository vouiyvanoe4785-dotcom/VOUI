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


class ExonerationTvaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("compta", password="x", role=Role.COMPTABLE)
        self.client.force_login(self.user)
        self.exonere = Partner.objects.create(
            raison_sociale="Zone Franche SA", exonere_tva=True,
            motif_exoneration="Zone franche - attestation n° ZF-42",
        )
        self.normal = Partner.objects.create(raison_sociale="Atlas Import")

    def post_invoice(self, client, pk=None, taux="20", extra=None):
        data = {
            "client": client.pk, "statut": "brouillon",
            "lignes-TOTAL_FORMS": "1", "lignes-INITIAL_FORMS": "0",
            "lignes-MIN_NUM_FORMS": "0", "lignes-MAX_NUM_FORMS": "1000",
            "lignes-0-type_frais": "honoraires", "lignes-0-designation": "Honoraires",
            "lignes-0-quantite": "1", "lignes-0-prix_unitaire": "1000", "lignes-0-taux_tva": taux,
        }
        data.update(extra or {})
        url = reverse("billing:invoice_update", args=[pk]) if pk else reverse("billing:invoice_create")
        return self.client.post(url, data, follow=True)

    def test_exempt_client_forces_zero_rate(self):
        resp = self.post_invoice(self.exonere, taux="20")
        invoice = Invoice.objects.get()
        self.assertTrue(invoice.exonere_tva)
        self.assertEqual(invoice.motif_exoneration, "Zone franche - attestation n° ZF-42")
        self.assertEqual(invoice.lignes.get().taux_tva, 0)
        self.assertEqual(invoice.montant_total, Decimal("1000.00"))
        self.assertContains(resp, "exonéré de TVA")
        self.assertContains(resp, "ZF-42")

    def test_normal_client_keeps_rate(self):
        self.post_invoice(self.normal, taux="20")
        invoice = Invoice.objects.get()
        self.assertFalse(invoice.exonere_tva)
        self.assertEqual(invoice.montant_total, Decimal("1200.00"))

    def test_switching_to_exempt_client_zeroes_untouched_lines(self):
        invoice = Invoice.objects.create(client=self.normal)
        line = InvoiceLine.objects.create(
            invoice=invoice, type_frais="honoraires", designation="H", prix_unitaire="1000", taux_tva=20
        )
        # Edit only the header: the existing line is submitted unchanged, so the formset skips it.
        self.post_invoice(self.exonere, pk=invoice.pk, extra={
            "lignes-INITIAL_FORMS": "1", "lignes-0-id": line.pk, "lignes-0-invoice": invoice.pk,
        })
        invoice.refresh_from_db()
        self.assertTrue(invoice.exonere_tva)
        self.assertEqual(invoice.montant_tva, Decimal("0"))

    def test_past_documents_are_not_rewritten(self):
        invoice = Invoice.objects.create(client=self.normal)
        line = InvoiceLine.objects.create(
            invoice=invoice, type_frais="honoraires", designation="H", prix_unitaire="1000", taux_tva=20
        )
        self.normal.exonere_tva = True
        self.normal.motif_exoneration = "Export"
        self.normal.save()

        # Editing the old invoice (e.g. to change its status) keeps the VAT it was issued with.
        self.post_invoice(self.normal, pk=invoice.pk, extra={
            "statut": "payee", "lignes-INITIAL_FORMS": "1",
            "lignes-0-id": line.pk, "lignes-0-invoice": invoice.pk,
        })
        invoice.refresh_from_db()
        self.assertEqual(invoice.statut, "payee")
        self.assertFalse(invoice.exonere_tva)
        self.assertEqual(invoice.montant_total, Decimal("1200.00"))

        # A new invoice for the now-exempt client is at 0 %.
        new = Invoice.objects.create(client=self.normal)
        new_line = InvoiceLine.objects.create(
            invoice=new, type_frais="honoraires", designation="H", prix_unitaire="1000", taux_tva=20
        )
        self.assertTrue(new.exonere_tva)
        self.assertEqual(new_line.taux_tva, 0)

    def test_quote_exemption_and_pdf_mention(self):
        quote = Quote.objects.create(client=self.exonere)
        QuoteLine.objects.create(quote=quote, type_frais="transport", designation="T", prix_unitaire="500", taux_tva=14)
        self.assertEqual(quote.montant_total, Decimal("500.00"))
        text = pdf_text(self.client.get(reverse("billing:quote_pdf", args=[quote.pk])).content)
        self.assertIn("Exonéré de TVA - Zone franche - attestation n° ZF-42", text)

    def test_form_exposes_exempt_clients(self):
        resp = self.client.get(reverse("billing:invoice_create"))
        self.assertContains(resp, 'id="clients-exoneres"')
        self.assertContains(resp, f"[{self.exonere.pk}]")


class PartnerExonerationFormTests(TestCase):
    def test_motif_required_when_exempt(self):
        from partners.forms import PartnerForm

        base = {"type_tiers": "client", "raison_sociale": "ZF", "pays": "Maroc", "is_active": True}
        form = PartnerForm(data={**base, "exonere_tva": True, "motif_exoneration": "  "})
        self.assertFalse(form.is_valid())
        self.assertIn("motif_exoneration", form.errors)
        form = PartnerForm(data={**base, "exonere_tva": True, "motif_exoneration": "Zone franche"})
        self.assertTrue(form.is_valid(), form.errors)
