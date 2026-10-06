from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User

from .models import Partner, PartnerType


class PartnerViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="agent", password="pass12345", role=Role.AGENT_TRANSIT
        )
        self.partner = Partner.objects.create(
            type_tiers=PartnerType.CLIENT, raison_sociale="Atlas Industries"
        )

    def test_list_requires_login(self):
        response = self.client.get(reverse("partners:list"))
        self.assertEqual(response.status_code, 302)

    def test_list_accessible_when_logged_in(self):
        self.client.login(username="agent", password="pass12345")
        response = self.client.get(reverse("partners:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Atlas Industries")

    def test_search_filters_by_raison_sociale(self):
        Partner.objects.create(type_tiers=PartnerType.FOURNISSEUR, raison_sociale="Maersk")
        self.client.login(username="agent", password="pass12345")
        response = self.client.get(reverse("partners:list"), {"q": "Maersk"})
        self.assertContains(response, "Maersk")
        self.assertNotContains(response, "Atlas Industries")

    def test_create_partner(self):
        self.client.login(username="agent", password="pass12345")
        response = self.client.post(
            reverse("partners:create"),
            {
                "type_tiers": PartnerType.CLIENT, "raison_sociale": "Nouveau Client SARL",
                "pays": "Maroc", "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Partner.objects.filter(raison_sociale="Nouveau Client SARL").exists())
