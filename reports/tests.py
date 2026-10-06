import csv
import datetime
from io import StringIO

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User
from billing.models import Invoice, InvoiceLine, StatutFacture
from dossiers.models import Dossier, TypeOperation
from partners.models import Partner
from purchasing.models import StatutAchat, SupplierInvoice, SupplierInvoiceLine

from .services import build_report


class VatReportTests(TestCase):
    def setUp(self):
        self.today = datetime.date.today()
        agent = User.objects.create_user("agent", password="x", service="Import")
        client = Partner.objects.create(raison_sociale="ACME")
        fournisseur = Partner.objects.create(raison_sociale="Port", type_tiers="prestataire")
        dossier = Dossier.objects.create(client=client, type_operation=TypeOperation.IMPORT, agent_responsable=agent)

        invoice = Invoice.objects.create(client=client, dossier=dossier, statut=StatutFacture.ENVOYEE)
        InvoiceLine.objects.create(invoice=invoice, type_frais="honoraires", designation="H", prix_unitaire="2000", taux_tva=20)
        InvoiceLine.objects.create(invoice=invoice, type_frais="droits_taxes", designation="D", prix_unitaire="5000", taux_tva=0)
        cancelled = Invoice.objects.create(client=client, dossier=dossier, statut=StatutFacture.ANNULEE)
        InvoiceLine.objects.create(invoice=cancelled, type_frais="honoraires", designation="H", prix_unitaire="9999", taux_tva=20)

        achat = SupplierInvoice.objects.create(fournisseur=fournisseur, dossier=dossier, statut=StatutAchat.VALIDEE)
        SupplierInvoiceLine.objects.create(invoice=achat, type_frais="debours", designation="M", prix_unitaire="500", taux_tva=20)

    def test_vat_summary(self):
        rows, totaux = build_report(self.today, self.today)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["service"], "Import")
        self.assertEqual(totaux["ca_ht"], 7000)
        self.assertEqual(totaux["tva_collectee"], 400)
        self.assertEqual(totaux["tva_deductible"], 100)
        self.assertEqual(totaux["tva_nette"], 300)
        self.assertEqual(totaux["ca_facture"], 7400)       # TTC
        self.assertEqual(totaux["depenses_engagees"], 600)  # TTC

    def test_page_and_csv(self):
        self.client.force_login(User.objects.create_user("compta", password="x", role=Role.COMPTABLE))
        params = {"date_debut": self.today.isoformat(), "date_fin": self.today.isoformat()}
        page = self.client.get(reverse("reports:service_report"), params)
        self.assertContains(page, "Synthèse TVA")
        self.assertContains(page, "à reverser")

        export = self.client.get(reverse("reports:service_report_export"), params)
        lines = list(csv.reader(StringIO(export.content.decode())))
        self.assertEqual(lines[0][-4:], [
            "CA facturé HT (MAD)", "TVA collectée (MAD)", "TVA déductible (MAD)", "TVA nette (MAD)",
        ])
        self.assertEqual(lines[-1][0], "TOTAL")
        self.assertEqual(lines[-1][-4:], ["7000.00", "400.00", "100.00", "300.00"])
