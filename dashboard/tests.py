from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User


class DashboardViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="compta", password="pass12345", role=Role.COMPTABLE
        )

    def test_requires_login(self):
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 302)

    def test_loads_for_authenticated_user(self):
        self.client.login(username="compta", password="pass12345")
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tableau de bord")
