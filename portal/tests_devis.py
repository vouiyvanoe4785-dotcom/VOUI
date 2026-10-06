import datetime

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role, User
from alerts.services import Categorie, collect_alertes
from billing.models import Quote, QuoteLine, StatutDevis
from billing.tests import pdf_text
from dossiers.models import Dossier, TypeOperation
from partners.models import Partner
from tracking.models import TypeEvenement


class QuoteAcceptanceTests(TestCase):
    def setUp(self):
        self.acme = Partner.objects.create(raison_sociale="ACME Import")
        self.client_user = User.objects.create_user(
            "acme", password="x", role=Role.CLIENT, partner=self.acme,
            first_name="Nadia", last_name="Alaoui", email="nadia@acme.ma",
        )
        self.commercial = User.objects.create_user("commercial", password="x", email="commercial@ayden.ma")
        self.agent = User.objects.create_user("agent", password="x", email="agent@ayden.ma")
        self.dossier = Dossier.objects.create(
            client=self.acme, type_operation=TypeOperation.IMPORT, agent_responsable=self.agent
        )
        self.quote = Quote.objects.create(
            client=self.acme, dossier=self.dossier, statut=StatutDevis.ENVOYE, created_by=self.commercial,
            date_validite=timezone.localdate() + datetime.timedelta(days=10),
        )
        QuoteLine.objects.create(quote=self.quote, type_frais="honoraires", designation="H", prix_unitaire="1000")
        self.url = reverse("portal:quote_detail", args=[self.quote.pk])
        self.client.force_login(self.client_user)

    def post(self, **data):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(self.url, data, follow=True)

    def test_accept(self):
        page = self.client.get(self.url)
        self.assertContains(page, "Accepter le devis")
        self.assertContains(page, 'value="Nadia Alaoui"')  # name pre-filled
        self.assertContains(self.client.get(reverse("portal:home")), "Devis en attente de votre réponse")

        resp = self.post(decision="accepter", nom="Nadia Alaoui", accord="on", commentaire="Go pour le 15")
        self.assertContains(resp, "votre accord a bien été enregistré")
        self.assertContains(resp, "Devis accepté")
        self.assertNotContains(resp, "Accepter le devis")

        self.quote.refresh_from_db()
        self.assertEqual(self.quote.statut, StatutDevis.ACCEPTE)
        self.assertEqual(self.quote.reponse_client_par, self.client_user)
        self.assertEqual(self.quote.reponse_client_nom, "Nadia Alaoui")

        event = self.dossier.evenements.get()
        self.assertEqual(event.type_evenement, TypeEvenement.DEVIS_ACCEPTE)
        self.assertTrue(event.visible_client)
        self.assertIn("Go pour le 15", event.commentaire)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["agent@ayden.ma", "commercial@ayden.ma"])
        self.assertIn("a accepté le devis", mail.outbox[0].subject)
        self.assertIn("Go pour le 15", mail.outbox[0].body)

        text = pdf_text(self.client.get(reverse("portal:quote_pdf", args=[self.quote.pk])).content)
        self.assertIn("Bon pour accord", text)
        self.assertIn("Nadia Alaoui", text)

        alertes = [a for a in collect_alertes(self.agent) if a.categorie == Categorie.REPONSE_DEVIS]
        self.assertEqual([(a.niveau, a.url) for a in alertes], [("info", self.quote.get_absolute_url())])

        self.client.force_login(self.agent)
        self.assertContains(self.client.get(self.quote.get_absolute_url()), "Accepté par le client depuis le portail")

    def test_accept_requires_checkbox_and_name(self):
        resp = self.post(decision="accepter", nom="")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Cochez la case pour confirmer votre accord.")
        self.assertIn("nom", resp.context["form"].errors)
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.statut, StatutDevis.ENVOYE)
        self.assertEqual(mail.outbox, [])

    def test_refuse_with_reason(self):
        self.post(decision="refuser", nom="Nadia Alaoui", commentaire="Trop cher")
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.statut, StatutDevis.REFUSE)
        self.assertEqual(self.dossier.evenements.get().type_evenement, TypeEvenement.DEVIS_REFUSE)
        alertes = [a for a in collect_alertes(self.agent) if a.categorie == Categorie.REPONSE_DEVIS]
        self.assertEqual(alertes[0].niveau, "warning")
        self.assertIn("Trop cher", alertes[0].detail)

    def test_cannot_answer_twice_or_when_expired(self):
        self.post(decision="accepter", nom="Nadia", accord="on")
        resp = self.post(decision="refuser", nom="Nadia")
        self.assertContains(resp, "Une réponse a déjà été donnée pour ce devis.")
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.statut, StatutDevis.ACCEPTE)
        self.assertEqual(self.dossier.evenements.count(), 1)

        expired = Quote.objects.create(
            client=self.acme, statut=StatutDevis.ENVOYE,
            date_validite=timezone.localdate() - datetime.timedelta(days=1),
        )
        url = reverse("portal:quote_detail", args=[expired.pk])
        self.assertContains(self.client.get(url), "Ce devis a expiré")
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(url, {"decision": "accepter", "nom": "Nadia", "accord": "on"}, follow=True)
        self.assertContains(resp, "Ce devis a expiré.")
        expired.refresh_from_db()
        self.assertEqual(expired.statut, StatutDevis.ENVOYE)

    def test_other_client_cannot_answer(self):
        other = Partner.objects.create(raison_sociale="Concurrent")
        intrus = User.objects.create_user("intrus", password="x", role=Role.CLIENT, partner=other)
        self.client.force_login(intrus)
        resp = self.client.post(self.url, {"decision": "refuser", "nom": "X"})
        self.assertEqual(resp.status_code, 404)
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.statut, StatutDevis.ENVOYE)

    def test_staff_event_form_hides_automatic_types(self):
        self.client.force_login(self.agent)
        resp = self.client.get(reverse("tracking:create", args=[self.dossier.pk]))
        choices = [c[0] for c in resp.context["form"].fields["type_evenement"].choices]
        self.assertNotIn(TypeEvenement.DEVIS_ACCEPTE, choices)
        self.assertNotIn(TypeEvenement.CHANGEMENT_STATUT, choices)
