from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role, User
from approvals.workflows import ensure_workflow
from billing.models import Invoice, InvoiceLine, Payment, Quote, StatutDevis, StatutFacture
from dossiers.models import Dossier, StatutDossier, TypeOperation
from partners.models import Partner
from purchasing.models import StatutAchat, SupplierInvoice, SupplierInvoiceLine
from tracking.models import DossierEvent, TypeEvenement

from .services import Categorie, collect_alertes


def by_cat(alertes, categorie):
    return [a for a in alertes if a.categorie == categorie]


@override_settings(
    ALERTE_DOSSIER_INACTIF_JOURS=7, ALERTE_FACTURE_RETARD_CRITIQUE_JOURS=30, ALERTE_ECHEANCE_PROCHE_JOURS=3,
)
class AlertesTests(TestCase):
    def setUp(self):
        cache.clear()
        self.today = timezone.localdate()
        self.agent = User.objects.create_user("agent", password="x", role=Role.AGENT_TRANSIT)
        self.compta = User.objects.create_user("compta", password="x", role=Role.COMPTABLE)
        self.client_tiers = Partner.objects.create(raison_sociale="Atlas Import")
        self.dossier = Dossier.objects.create(
            client=self.client_tiers, type_operation=TypeOperation.IMPORT, agent_responsable=self.agent
        )
        DossierEvent.objects.create(dossier=self.dossier, type_evenement=TypeEvenement.NOTE)

    def invoice(self, echeance_jours, montant="1000", statut=StatutFacture.ENVOYEE):
        invoice = Invoice.objects.create(
            client=self.client_tiers, dossier=self.dossier, statut=statut,
            date_echeance=self.today + timedelta(days=echeance_jours),
        )
        InvoiceLine.objects.create(
            invoice=invoice, type_frais="debours", designation="x", prix_unitaire=montant, taux_tva=0
        )
        return invoice

    def test_overdue_invoices(self):
        self.invoice(5)                                          # not due yet
        late = self.invoice(-10)                                 # warning
        very_late = self.invoice(-45)                            # danger
        self.invoice(-10, statut=StatutFacture.BROUILLON)        # draft: ignored
        paid = self.invoice(-10)
        Payment.objects.create(invoice=paid, montant="1000", date_paiement=self.today)

        alertes = by_cat(collect_alertes(self.agent), Categorie.FACTURE_ECHUE)
        self.assertEqual([a.url for a in alertes], [very_late.get_absolute_url(), late.get_absolute_url()])
        self.assertEqual([a.niveau for a in alertes], ["danger", "warning"])
        self.assertIn("Échue depuis 10 jours", alertes[1].detail)
        self.assertIn("1 000,00 MAD", alertes[1].detail)
        self.assertEqual(alertes[0].agent_id, self.agent.pk)

    def test_inactive_dossier_and_incident(self):
        later = timezone.now() + timedelta(days=8)
        alertes = by_cat(collect_alertes(self.agent, now=later), Categorie.DOSSIER_INACTIF)
        self.assertEqual(len(alertes), 1)
        self.assertIn("8 jours", alertes[0].detail)
        self.assertEqual(by_cat(collect_alertes(self.agent), Categorie.DOSSIER_INACTIF), [])

        # A recent event clears the inactivity alert...
        DossierEvent.objects.create(
            dossier=self.dossier, type_evenement=TypeEvenement.INCIDENT,
            commentaire="Conteneur bloqué", date_evenement=later,
        )
        alertes = collect_alertes(self.agent, now=later)
        self.assertEqual(by_cat(alertes, Categorie.DOSSIER_INACTIF), [])
        # ...but an incident as the latest event raises a danger alert until something follows it.
        incidents = by_cat(alertes, Categorie.INCIDENT)
        self.assertEqual([(a.niveau, a.detail) for a in incidents], [("danger", "Conteneur bloqué")])

        DossierEvent.objects.create(
            dossier=self.dossier, type_evenement=TypeEvenement.BAE, date_evenement=later + timedelta(hours=1)
        )
        self.assertEqual(by_cat(collect_alertes(self.agent, now=later), Categorie.INCIDENT), [])

    def test_closed_dossiers_are_ignored(self):
        self.dossier.statut = StatutDossier.CLOTURE
        self.dossier.save()
        later = timezone.now() + timedelta(days=30)
        self.assertEqual(by_cat(collect_alertes(self.agent, now=later), Categorie.DOSSIER_INACTIF), [])

    def test_quotes_to_follow_up(self):
        def quote(jours, statut=StatutDevis.ENVOYE):
            return Quote.objects.create(
                client=self.client_tiers, statut=statut, date_validite=self.today + timedelta(days=jours)
            )
        expired, soon = quote(-2), quote(2)
        quote(10)                                     # far away
        quote(-2, statut=StatutDevis.ACCEPTE)         # answered
        alertes = by_cat(collect_alertes(self.agent), Categorie.DEVIS)
        self.assertEqual(
            [(a.url, a.niveau) for a in alertes],
            [(expired.get_absolute_url(), "warning"), (soon.get_absolute_url(), "info")],
        )

    def test_supplier_invoices_only_for_billing_roles(self):
        fournisseur = Partner.objects.create(raison_sociale="Transports Sud", type_tiers="transporteur")
        achat = SupplierInvoice.objects.create(
            fournisseur=fournisseur, statut=StatutAchat.VALIDEE, date_echeance=self.today - timedelta(days=1)
        )
        SupplierInvoiceLine.objects.create(
            invoice=achat, type_frais="transport", designation="Transport", prix_unitaire="800"
        )
        self.assertEqual(len(by_cat(collect_alertes(self.compta), Categorie.ACHAT)), 1)
        self.assertEqual(by_cat(collect_alertes(self.agent), Categorie.ACHAT), [])

    def test_validations_for_role(self):
        ensure_workflow(self.dossier)  # step 1: comptable, step 2: direction (blocked)
        direction = User.objects.create_user("dir", password="x", role=Role.DIRECTION)
        self.assertEqual(len(by_cat(collect_alertes(self.compta), Categorie.VALIDATION)), 1)
        self.assertEqual(by_cat(collect_alertes(direction), Categorie.VALIDATION), [])
        self.assertEqual(by_cat(collect_alertes(self.agent), Categorie.VALIDATION), [])

    def test_pages(self):
        invoice = self.invoice(-45)
        self.client.force_login(self.agent)
        resp = self.client.get(reverse("alerts:list"))
        self.assertContains(resp, "Factures échues (1)")
        self.assertContains(resp, invoice.reference)
        self.assertContains(self.client.get(reverse("alerts:list") + "?categorie=devis"), "Aucune alerte")
        other = User.objects.create_user("other", password="x")
        self.client.force_login(other)
        self.assertContains(self.client.get(reverse("alerts:list") + "?mine=1"), "Aucune alerte")

        cache.clear()
        self.client.force_login(self.agent)
        home = self.client.get(reverse("dashboard:home"))
        self.assertContains(home, "À traiter en priorité")
        self.assertEqual(home.context["alertes_compte"], {"total": 1, "urgentes": 1})
