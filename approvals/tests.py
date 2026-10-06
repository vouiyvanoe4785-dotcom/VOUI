from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User
from dossiers.models import Dossier, TypeOperation
from partners.models import Partner, PartnerType

from .models import EtapeStatut, ValidationStep
from .workflows import ensure_workflow, get_steps


class EnsureWorkflowTests(TestCase):
    def setUp(self):
        client_partner = Partner.objects.create(
            type_tiers=PartnerType.CLIENT, raison_sociale="Atlas Industries"
        )
        self.dossier = Dossier.objects.create(
            client=client_partner, type_operation=TypeOperation.IMPORT
        )

    def test_creates_ordered_steps_for_known_model(self):
        steps = ensure_workflow(self.dossier)
        self.assertEqual([s.ordre for s in steps], [1, 2])
        self.assertEqual(steps[0].role_requis, Role.COMPTABLE)
        self.assertEqual(steps[1].role_requis, Role.DIRECTION)

    def test_is_idempotent(self):
        ensure_workflow(self.dossier)
        ensure_workflow(self.dossier)
        self.assertEqual(get_steps(self.dossier).__len__(), 2)

    def test_unknown_model_returns_no_steps(self):
        partner = Partner.objects.create(type_tiers=PartnerType.CLIENT, raison_sociale="X")
        self.assertEqual(ensure_workflow(partner), [])


class ValidationActionViewTests(TestCase):
    def setUp(self):
        self.comptable = User.objects.create_user(
            username="compta", password="pass12345", role=Role.COMPTABLE,
            first_name="Sara", last_name="Comptable",
        )
        self.direction = User.objects.create_user(
            username="direction", password="pass12345", role=Role.DIRECTION,
            first_name="Yassine", last_name="Direction",
        )
        self.agent = User.objects.create_user(
            username="agent", password="pass12345", role=Role.AGENT_TRANSIT
        )
        client_partner = Partner.objects.create(
            type_tiers=PartnerType.CLIENT, raison_sociale="Atlas Industries"
        )
        self.dossier = Dossier.objects.create(
            client=client_partner, type_operation=TypeOperation.IMPORT
        )
        self.steps = ensure_workflow(self.dossier)
        self.step1, self.step2 = self.steps

    def _act(self, user, step, action, commentaire="", signature_nom=""):
        self.client.login(username=user.username, password="pass12345")
        response = self.client.post(
            reverse("approvals:action", kwargs={"pk": step.pk}),
            {"action": action, "commentaire": commentaire, "signature_nom": signature_nom},
        )
        self.client.logout()
        return response

    def test_wrong_role_cannot_approve_step(self):
        self._act(self.direction, self.step1, "approuver", signature_nom="Yassine Direction")
        self.step1.refresh_from_db()
        self.assertEqual(self.step1.statut, EtapeStatut.EN_ATTENTE)

    def test_second_step_blocked_until_first_is_approved(self):
        self._act(self.direction, self.step2, "approuver", signature_nom="Yassine Direction")
        self.step2.refresh_from_db()
        self.assertEqual(self.step2.statut, EtapeStatut.EN_ATTENTE)

    def test_sequential_approval_completes_workflow_and_validates_dossier(self):
        self._act(self.comptable, self.step1, "approuver", signature_nom="Sara Comptable")
        self.step1.refresh_from_db()
        self.dossier.refresh_from_db()
        self.assertEqual(self.step1.statut, EtapeStatut.APPROUVEE)
        self.assertFalse(self.dossier.valide)

        self._act(self.direction, self.step2, "approuver", signature_nom="Yassine Direction")
        self.step2.refresh_from_db()
        self.dossier.refresh_from_db()
        self.assertEqual(self.step2.statut, EtapeStatut.APPROUVEE)
        self.assertTrue(self.dossier.valide)
        self.assertEqual(self.dossier.valide_par, self.direction)

    def test_rejection_requires_comment(self):
        response = self._act(self.comptable, self.step1, "refuser", commentaire="")
        self.step1.refresh_from_db()
        self.assertEqual(self.step1.statut, EtapeStatut.EN_ATTENTE)
        self.assertEqual(response.status_code, 302)

    def test_rejection_with_comment_blocks_workflow(self):
        self._act(self.comptable, self.step1, "refuser", commentaire="Documents incomplets")
        self.step1.refresh_from_db()
        self.dossier.refresh_from_db()
        self.assertEqual(self.step1.statut, EtapeStatut.REFUSEE)
        self.assertFalse(self.dossier.valide)

    def test_admin_can_override_any_role(self):
        admin = User.objects.create_user(username="admin1", password="pass12345", role=Role.ADMIN)
        self._act(admin, self.step1, "approuver", signature_nom="Admin")
        self.step1.refresh_from_db()
        self.assertEqual(self.step1.statut, EtapeStatut.APPROUVEE)

    def test_already_treated_step_cannot_be_treated_again(self):
        self._act(self.comptable, self.step1, "approuver", signature_nom="Sara Comptable")
        self._act(self.comptable, self.step1, "refuser", commentaire="essai")
        self.step1.refresh_from_db()
        self.assertEqual(self.step1.statut, EtapeStatut.APPROUVEE)


class StartValidationViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="agent", password="pass12345", role=Role.AGENT_TRANSIT
        )
        client_partner = Partner.objects.create(
            type_tiers=PartnerType.CLIENT, raison_sociale="Atlas Industries"
        )
        self.dossier = Dossier.objects.create(
            client=client_partner, type_operation=TypeOperation.IMPORT
        )

    def test_requires_login(self):
        ct = ContentType.objects.get_for_model(Dossier)
        response = self.client.post(
            reverse("approvals:start", kwargs={"content_type_id": ct.id, "object_id": self.dossier.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_starts_workflow_for_dossier(self):
        self.client.login(username="agent", password="pass12345")
        ct = ContentType.objects.get_for_model(Dossier)
        response = self.client.post(
            reverse("approvals:start", kwargs={"content_type_id": ct.id, "object_id": self.dossier.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ValidationStep.objects.filter(object_id=self.dossier.pk).count(), 2)
