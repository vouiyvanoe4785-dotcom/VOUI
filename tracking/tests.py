from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User
from dossiers.models import Dossier, StatutDossier, TypeOperation
from partners.models import Partner

from .models import DossierEvent, TypeEvenement


class TrackingTestCase(TestCase):
    def setUp(self):
        self.agent = User.objects.create_user("agent", password="pass", role=Role.AGENT_TRANSIT)
        self.client.force_login(self.agent)
        self.partner = Partner.objects.create(raison_sociale="Import SARL")
        self.dossier = Dossier.objects.create(
            client=self.partner, type_operation=TypeOperation.IMPORT, created_by=self.agent
        )

    def test_create_dossier_logs_opening_event(self):
        self.client.post(reverse("dossiers:create"), {
            "client": self.partner.pk, "type_operation": TypeOperation.EXPORT,
            "statut": StatutDossier.OUVERT,
        })
        dossier = Dossier.objects.exclude(pk=self.dossier.pk).get()
        event = dossier.evenements.get()
        self.assertTrue(event.automatique)
        self.assertEqual(event.nouveau_statut, StatutDossier.OUVERT)

    def test_update_logs_status_change_only_when_changed(self):
        data = {
            "client": self.partner.pk, "type_operation": TypeOperation.IMPORT,
            "statut": StatutDossier.OUVERT, "notes": "rien",
        }
        url = reverse("dossiers:update", args=[self.dossier.pk])
        self.client.post(url, data)
        self.assertFalse(self.dossier.evenements.exists())

        data["statut"] = StatutDossier.EN_DOUANE
        self.client.post(url, data)
        event = self.dossier.evenements.get()
        self.assertEqual(event.type_evenement, TypeEvenement.CHANGEMENT_STATUT)
        self.assertEqual(event.ancien_statut, StatutDossier.OUVERT)
        self.assertEqual(event.nouveau_statut, StatutDossier.EN_DOUANE)

    def test_add_event_with_status_change(self):
        resp = self.client.post(reverse("tracking:create", args=[self.dossier.pk]), {
            "type_evenement": TypeEvenement.BAE, "date_evenement": "2026-10-01T10:30",
            "lieu": "Port de Casablanca", "commentaire": "BAE reçu",
            "changer_statut": StatutDossier.LIVRE,
        })
        self.assertRedirects(resp, self.dossier.get_absolute_url() + "#suivi", fetch_redirect_response=False)
        self.dossier.refresh_from_db()
        self.assertEqual(self.dossier.statut, StatutDossier.LIVRE)
        types = set(self.dossier.evenements.values_list("type_evenement", flat=True))
        self.assertEqual(types, {TypeEvenement.BAE, TypeEvenement.CHANGEMENT_STATUT})

    def test_consultation_role_cannot_add_event(self):
        viewer = User.objects.create_user("viewer", password="pass", role=Role.CONSULTATION)
        self.client.force_login(viewer)
        resp = self.client.post(reverse("tracking:create", args=[self.dossier.pk]), {
            "type_evenement": TypeEvenement.NOTE, "date_evenement": "2026-10-01T10:30",
        })
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(self.dossier.evenements.exists())

    def test_delete_restricted_to_author_and_manual_events(self):
        mine = DossierEvent.objects.create(
            dossier=self.dossier, type_evenement=TypeEvenement.NOTE, created_by=self.agent
        )
        auto = DossierEvent.objects.create(
            dossier=self.dossier, type_evenement=TypeEvenement.CHANGEMENT_STATUT,
            automatique=True, created_by=self.agent,
        )
        other = User.objects.create_user("other", password="pass")
        theirs = DossierEvent.objects.create(
            dossier=self.dossier, type_evenement=TypeEvenement.NOTE, created_by=other
        )
        self.assertEqual(self.client.post(reverse("tracking:delete", args=[auto.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("tracking:delete", args=[theirs.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("tracking:delete", args=[mine.pk])).status_code, 302)
        self.assertEqual(set(DossierEvent.objects.values_list("pk", flat=True)), {auto.pk, theirs.pk})

    def test_pages_render(self):
        DossierEvent.objects.create(
            dossier=self.dossier, type_evenement=TypeEvenement.INCIDENT,
            commentaire="Conteneur bloqué", created_by=self.agent,
        )
        for url in (
            reverse("tracking:activity"),
            reverse("tracking:activity") + "?type=incident&mine=1",
            self.dossier.get_absolute_url(),
            reverse("dashboard:home"),
            reverse("tracking:create", args=[self.dossier.pk]),
        ):
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, url)
        self.assertContains(self.client.get(reverse("tracking:activity")), "Conteneur bloqué")
