import datetime
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User
from billing.models import Invoice, InvoiceLine, Payment, TypeFrais
from dossiers.models import Dossier, TypeOperation
from partners.models import Partner, PartnerType
from purchasing.models import SupplierInvoice, SupplierInvoiceLine, SupplierPayment

from .services import NON_AFFECTE, build_report


class BuildReportTests(TestCase):
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
            prix_unitaire=Decimal("5000"),
        )
        Payment.objects.create(invoice=inv1, montant=Decimal("3000"), date_paiement=today)

        inv2 = Invoice.objects.create(client=self.client_partner, dossier=self.d_export)
        InvoiceLine.objects.create(
            invoice=inv2, type_frais=TypeFrais.HONORAIRES, designation="H", quantite=1,
            prix_unitaire=Decimal("2500"),
        )
        Payment.objects.create(invoice=inv2, montant=Decimal("2500"), date_paiement=today)

        inv3 = Invoice.objects.create(client=self.client_partner, dossier=self.d_non_affecte)
        InvoiceLine.objects.create(
            invoice=inv3, type_frais=TypeFrais.HONORAIRES, designation="H", quantite=1,
            prix_unitaire=Decimal("22000"),
        )

        ach1 = SupplierInvoice.objects.create(
            fournisseur=self.fournisseur, dossier=self.d_import, date_facture=today
        )
        SupplierInvoiceLine.objects.create(
            invoice=ach1, type_frais=TypeFrais.TRANSPORT, designation="Fret", quantite=1,
            prix_unitaire=Decimal("1800"),
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
