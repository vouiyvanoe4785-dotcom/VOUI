from datetime import timedelta
from io import StringIO

from django.core import mail
from django.core.management import CommandError, call_command
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import Role, User
from billing.models import Invoice, InvoiceLine, StatutFacture
from dossiers.models import Dossier, TypeOperation
from partners.models import Partner
from tracking.models import DossierEvent, TypeEvenement

from .recap import alertes_pour


@override_settings(SITE_URL="https://transit.example.ma", ALERTE_FACTURE_RETARD_CRITIQUE_JOURS=30)
class RecapAlertesTests(TestCase):
    def setUp(self):
        cache.clear()
        mk = User.objects.create_user
        self.agent = mk("agent", password="x", email="agent@ayden.ma", role=Role.AGENT_TRANSIT, first_name="Karim")
        self.collegue = mk("collegue", password="x", email="collegue@ayden.ma", role=Role.AGENT_TRANSIT)
        self.compta = mk("compta", password="x", email="compta@ayden.ma", role=Role.COMPTABLE)
        self.direction = mk("dir", password="x", email="dir@ayden.ma", role=Role.DIRECTION)
        self.sans_email = mk("sansmail", password="x", role=Role.DIRECTION)
        self.desabonne = mk("desabonne", password="x", email="d@ayden.ma", role=Role.DIRECTION, recap_alertes_email=False)
        partner = Partner.objects.create(raison_sociale="ACME")
        mk("client", password="x", email="c@acme.ma", role=Role.CLIENT, partner=partner)

        self.dossier = Dossier.objects.create(client=partner, type_operation=TypeOperation.IMPORT, agent_responsable=self.agent)
        DossierEvent.objects.create(dossier=self.dossier, type_evenement=TypeEvenement.INCIDENT, commentaire="Conteneur bloqué")
        invoice = Invoice.objects.create(
            client=partner, statut=StatutFacture.ENVOYEE, date_echeance=timezone.localdate() - timedelta(days=40)
        )  # no dossier: nobody's own alert
        InvoiceLine.objects.create(invoice=invoice, type_frais="debours", designation="x", prix_unitaire="500", taux_tva=0)

    def categories(self, user):
        return sorted(a.categorie for a in alertes_pour(user))

    def test_who_gets_what(self):
        self.assertEqual(self.categories(self.agent), ["incident"])           # own dossier only
        self.assertEqual(self.categories(self.collegue), [])                  # nothing of theirs
        self.assertEqual(self.categories(self.compta), ["facture_echue"])     # money matters
        self.assertEqual(self.categories(self.direction), ["facture_echue", "incident"])  # everything

    def test_command_sends_one_mail_per_concerned_user(self):
        out = StringIO()
        call_command("envoyer_alertes", stdout=out)
        recipients = sorted(m.to[0] for m in mail.outbox)
        self.assertEqual(recipients, ["agent@ayden.ma", "compta@ayden.ma", "dir@ayden.ma"])
        self.assertIn("3 e-mail(s) envoyé(s)", out.getvalue())

        message = next(m for m in mail.outbox if m.to == ["dir@ayden.ma"])
        self.assertIn("2 alertes dont 2 urgentes", message.subject)
        self.assertIn("== Incidents ouverts (1) ==", message.body)
        self.assertIn("[URGENT] ", message.body)
        self.assertIn(f"https://transit.example.ma{self.dossier.get_absolute_url()}#suivi", message.body)
        self.assertIn("Conteneur bloqué", message.body)

        agent_mail = next(m for m in mail.outbox if m.to == ["agent@ayden.ma"])
        self.assertIn("Bonjour Karim", agent_mail.body)
        self.assertNotIn("Factures échues", agent_mail.body)

    def test_dry_run_and_single_user(self):
        out = StringIO()
        call_command("envoyer_alertes", "--dry-run", stdout=out)
        self.assertEqual(mail.outbox, [])
        self.assertIn("dir <dir@ayden.ma> recevrait 2 alerte(s)", out.getvalue())

        call_command("envoyer_alertes", "--utilisateur", "agent", stdout=StringIO())
        self.assertEqual([m.to for m in mail.outbox], [["agent@ayden.ma"]])

        with self.assertRaisesMessage(CommandError, "ne reçoit pas le récapitulatif"):
            call_command("envoyer_alertes", "--utilisateur", "desabonne")
        with self.assertRaisesMessage(CommandError, "Utilisateur inconnu"):
            call_command("envoyer_alertes", "--utilisateur", "personne")

    def test_nothing_to_report_sends_nothing(self):
        Invoice.objects.all().delete()
        DossierEvent.objects.create(dossier=self.dossier, type_evenement=TypeEvenement.BAE)
        call_command("envoyer_alertes", stdout=StringIO())
        self.assertEqual(mail.outbox, [])
