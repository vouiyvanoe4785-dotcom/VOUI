from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User
from dossiers.models import Dossier, TypeOperation
from partners.models import Partner, PartnerType

from .models import Marchandise


class MarchandiseViewsTests(TestCase):
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

    def test_create_requires_login(self):
        response = self.client.get(reverse("cargo:create", kwargs={"dossier_pk": self.dossier.pk}))
        self.assertEqual(response.status_code, 302)

    def test_create_marchandise_links_to_dossier(self):
        self.client.login(username="agent", password="pass12345")
        response = self.client.post(
            reverse("cargo:create", kwargs={"dossier_pk": self.dossier.pk}),
            {
                "designation": "Pièces mécaniques", "code_hs": "8483.40",
                "quantite": "10", "unite": "colis", "devise": "MAD",
            },
        )
        self.assertEqual(response.status_code, 302)
        marchandise = Marchandise.objects.get()
        self.assertEqual(marchandise.dossier, self.dossier)
        self.assertEqual(marchandise.designation, "Pièces mécaniques")

    def test_update_redirects_to_dossier(self):
        marchandise = Marchandise.objects.create(
            dossier=self.dossier, designation="Pièces", quantite=1
        )
        self.client.login(username="agent", password="pass12345")
        response = self.client.post(
            reverse("cargo:update", kwargs={"pk": marchandise.pk}),
            {
                "designation": "Pièces modifiées", "code_hs": "", "quantite": "2",
                "unite": "colis", "devise": "MAD",
            },
        )
        self.assertEqual(response.status_code, 302)
        marchandise.refresh_from_db()
        self.assertEqual(marchandise.designation, "Pièces modifiées")
