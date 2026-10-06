import csv
import datetime
from decimal import Decimal
from io import StringIO

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User
from billing.models import Invoice, InvoiceLine, Payment, StatutFacture, TypeFrais
from dossiers.models import Dossier, TypeOperation
from partners.models import Partner, PartnerType
from purchasing.models import StatutAchat, SupplierInvoice, SupplierInvoiceLine, SupplierPayment

from .services import NON_AFFECTE, build_report


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


class BuildReportTests(TestCase):
    """Non-VAT sanity checks: every line is pinned to taux_tva=0 so HT == TTC
    (VAT math is covered by VatReportTests above)."""

    def setUp(self):
        self.client_partner = Partner.objects.create(
            type_tiers=PartnerType.CLIENT, raison_sociale="Atlas Industries"
        )
        self.fournisseur = Partner.objects.create(
            type_tiers=PartnerType.FOURNISSEUR, raison_sociale="CMA CGM"
        )
        self.agent_import = User.objects.create_user(
            username="agent_import", password="x", role=Role.AGENT_TRANSIT, service="Import"
        )
        self.agent_export = User.objects.create_user(
            username="agent_export", password="x", role=Role.AGENT_TRANSIT, service="Export"
        )

        self.d_import = Dossier.objects.create(
            client=self.client_partner, type_operation=TypeOperation.IMPORT,
            agent_responsable=self.agent_import,
        )
        self.d_export = Dossier.objects.create(
            client=self.client_partner, type_operation=TypeOperation.EXPORT,
            agent_responsable=self.agent_export,
        )
        self.d_non_affecte = Dossier.objects.create(
            client=self.client_partner, type_operation=TypeOperation.TRANSIT,
        )

        today = datetime.date.today()
        self.today = today

        inv1 = Invoice.objects.create(client=self.client_partner, dossier=self.d_import)
        InvoiceLine.objects.create(
            invoice=inv1, type_frais=TypeFrais.HONORAIRES, designation="H", quantite=1,
            prix_unitaire=Decimal("5000"), taux_tva=0,
        )
        Payment.objects.create(invoice=inv1, montant=Decimal("3000"), date_paiement=today)

        inv2 = Invoice.objects.create(client=self.client_partner, dossier=self.d_export)
        InvoiceLine.objects.create(
            invoice=inv2, type_frais=TypeFrais.HONORAIRES, designation="H", quantite=1,
            prix_unitaire=Decimal("2500"), taux_tva=0,
        )
        Payment.objects.create(invoice=inv2, montant=Decimal("2500"), date_paiement=today)

        inv3 = Invoice.objects.create(client=self.client_partner, dossier=self.d_non_affecte)
        InvoiceLine.objects.create(
            invoice=inv3, type_frais=TypeFrais.HONORAIRES, designation="H", quantite=1,
            prix_unitaire=Decimal("22000"), taux_tva=0,
        )

        ach1 = SupplierInvoice.objects.create(
            fournisseur=self.fournisseur, dossier=self.d_import, date_facture=today
        )
        SupplierInvoiceLine.objects.create(
            invoice=ach1, type_frais=TypeFrais.TRANSPORT, designation="Fret", quantite=1,
            prix_unitaire=Decimal("1800"), taux_tva=0,
        )
        SupplierPayment.objects.create(invoice=ach1, montant=Decimal("1800"), date_paiement=today)

        self.period_start = today - datetime.timedelta(days=1)
        self.period_end = today + datetime.timedelta(days=1)

    def test_rollup_matches_expected_totals_per_service(self):
        rows, totaux = build_report(self.period_start, self.period_end)
        by_service = {row["service"]: row for row in rows}

        self.assertEqual(by_service["Import"]["nb_dossiers"], 1)
        self.assertEqual(by_service["Import"]["ca_facture"], Decimal("5000"))
        self.assertEqual(by_service["Import"]["ca_encaisse"], Decimal("3000"))
        self.assertEqual(by_service["Import"]["depenses_engagees"], Decimal("1800"))
        self.assertEqual(by_service["Import"]["depenses_payees"], Decimal("1800"))
        self.assertEqual(by_service["Import"]["resultat"], Decimal("1200"))

        self.assertEqual(by_service["Export"]["ca_facture"], Decimal("2500"))
        self.assertEqual(by_service["Export"]["ca_encaisse"], Decimal("2500"))
        self.assertEqual(by_service["Export"]["resultat"], Decimal("2500"))

        self.assertEqual(by_service[NON_AFFECTE]["ca_facture"], Decimal("22000"))
        self.assertEqual(by_service[NON_AFFECTE]["ca_encaisse"], Decimal("0"))

        self.assertEqual(totaux["nb_dossiers"], 3)
        self.assertEqual(totaux["ca_facture"], Decimal("29500"))
        self.assertEqual(totaux["ca_encaisse"], Decimal("5500"))
        self.assertEqual(totaux["depenses_payees"], Decimal("1800"))
        self.assertEqual(totaux["resultat"], Decimal("3700"))

    def test_service_filter_narrows_to_one_row(self):
        rows, totaux = build_report(self.period_start, self.period_end, service="Import")
        self.assertEqual([r["service"] for r in rows], ["Import"])
        self.assertEqual(totaux["nb_dossiers"], 1)

    def test_outside_period_is_excluded(self):
        rows, totaux = build_report(
            datetime.date(2000, 1, 1), datetime.date(2000, 1, 31)
        )
        self.assertEqual(rows, [])
        self.assertEqual(totaux["nb_dossiers"], 0)


class ReportAccessControlTests(TestCase):
    def setUp(self):
        self.comptable = User.objects.create_user(
            username="compta", password="pass12345", role=Role.COMPTABLE
        )
        self.agent = User.objects.create_user(
            username="agent", password="pass12345", role=Role.AGENT_TRANSIT
        )

    def test_agent_cannot_access_report(self):
        self.client.login(username="agent", password="pass12345")
        response = self.client.get(reverse("reports:service_report"))
        self.assertEqual(response.status_code, 403)

    def test_comptable_can_access_report(self):
        self.client.login(username="compta", password="pass12345")
        response = self.client.get(reverse("reports:service_report"))
        self.assertEqual(response.status_code, 200)

    def test_csv_export_requires_billing_role(self):
        self.client.login(username="agent", password="pass12345")
        response = self.client.get(reverse("reports:service_report_export"))
        self.assertEqual(response.status_code, 403)

    def test_csv_export_returns_csv_content_type(self):
        self.client.login(username="compta", password="pass12345")
        response = self.client.get(reverse("reports:service_report_export"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
