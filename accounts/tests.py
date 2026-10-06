from django.test import TestCase
from django.urls import reverse

from .models import Role, User


class UserRoleHelpersTests(TestCase):
    def test_is_admin_role_for_admin_role(self):
        user = User.objects.create_user(username="a", password="x", role=Role.ADMIN)
        self.assertTrue(user.is_admin_role())

    def test_is_admin_role_for_superuser_regardless_of_role(self):
        user = User.objects.create_superuser(
            username="root", password="x", email="root@example.com"
        )
        user.role = Role.AGENT_TRANSIT
        user.save()
        self.assertTrue(user.is_admin_role())

    def test_is_admin_role_false_for_regular_agent(self):
        user = User.objects.create_user(username="agent", password="x", role=Role.AGENT_TRANSIT)
        self.assertFalse(user.is_admin_role())

    def test_can_manage_billing_roles(self):
        allowed = [Role.ADMIN, Role.COMPTABLE, Role.DIRECTION]
        for role in allowed:
            user = User.objects.create_user(username=f"u-{role}", password="x", role=role)
            self.assertTrue(user.can_manage_billing(), role)

        denied = User.objects.create_user(username="agent2", password="x", role=Role.AGENT_TRANSIT)
        self.assertFalse(denied.can_manage_billing())


class TeamViewsPermissionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin1", password="pass12345", role=Role.ADMIN
        )
        self.agent = User.objects.create_user(
            username="agent1", password="pass12345", role=Role.AGENT_TRANSIT
        )

    def test_login_page_accessible_without_auth(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)

    def test_team_list_requires_login(self):
        response = self.client.get(reverse("accounts:team_list"))
        self.assertEqual(response.status_code, 302)

    def test_team_list_forbidden_for_non_admin(self):
        self.client.login(username="agent1", password="pass12345")
        response = self.client.get(reverse("accounts:team_list"))
        self.assertEqual(response.status_code, 403)

    def test_team_list_allowed_for_admin(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(reverse("accounts:team_list"))
        self.assertEqual(response.status_code, 200)

    def test_team_create_forbidden_for_non_admin(self):
        self.client.login(username="agent1", password="pass12345")
        response = self.client.post(
            reverse("accounts:team_create"),
            {
                "username": "newbie", "password1": "SuperSecret123", "password2": "SuperSecret123",
                "role": Role.AGENT_TRANSIT,
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username="newbie").exists())
