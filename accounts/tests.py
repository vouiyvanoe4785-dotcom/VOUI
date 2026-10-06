import re

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import Societe
from partners.models import Partner

from .models import Role, User

NEW_PASSWORD = "Nouveau-mot-de-passe-2026"


def reset_link(message):
    return re.search(r"https?://[^/\s]+(/comptes/mot-de-passe/reinitialiser/\S+)", message.body).group(1)


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


@override_settings(PASSWORD_RESET_TIMEOUT=60 * 60 * 24)
class PasswordResetTests(TestCase):
    def setUp(self):
        societe = Societe.load()
        societe.raison_sociale = "Ayden Transit SARL"
        societe.save()
        self.user = User.objects.create_user("nadia", email="nadia@acme.ma", password="ancien-mdp-123")

    def test_full_reset_flow(self):
        resp = self.client.post(reverse("accounts:password_reset"), {"email": "nadia@acme.ma"})
        self.assertRedirects(resp, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["nadia@acme.ma"])
        self.assertIn("Ayden Transit SARL", message.subject)
        self.assertIn("identifiant : nadia", message.body)
        self.assertIn("expire dans 24 heures", message.body)

        # Django swaps the token for a session value and redirects to a "set-password" URL.
        resp = self.client.get(reset_link(message), follow=True)
        self.assertTrue(resp.context["validlink"])
        resp = self.client.post(resp.request["PATH_INFO"], {
            "new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD,
        })
        self.assertRedirects(resp, reverse("accounts:password_reset_complete"))
        self.assertTrue(self.client.login(username="nadia", password=NEW_PASSWORD))

        # The link only works once.
        self.client.logout()
        resp = self.client.get(reset_link(message), follow=True)
        self.assertFalse(resp.context["validlink"])
        self.assertContains(resp, "Ce lien n'est plus valable")

    def test_unknown_address_gives_same_answer_and_sends_nothing(self):
        resp = self.client.post(reverse("accounts:password_reset"), {"email": "inconnu@example.com"})
        self.assertRedirects(resp, reverse("accounts:password_reset_done"))
        self.assertEqual(mail.outbox, [])

    def test_login_page_links_to_reset(self):
        self.assertContains(self.client.get(reverse("accounts:login")), reverse("accounts:password_reset"))


class PasswordChangeTests(TestCase):
    def test_staff_change(self):
        user = User.objects.create_user("agent", password="ancien-mdp-123")
        self.client.force_login(user)
        resp = self.client.get(reverse("accounts:password_change"))
        self.assertTemplateUsed(resp, "base.html")
        resp = self.client.post(reverse("accounts:password_change"), {
            "old_password": "ancien-mdp-123", "new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD,
        })
        self.assertRedirects(resp, reverse("dashboard:home"), fetch_redirect_response=False)
        user.refresh_from_db()
        self.assertTrue(user.check_password(NEW_PASSWORD))

    def test_client_change_stays_in_portal(self):
        partner = Partner.objects.create(raison_sociale="ACME")
        user = User.objects.create_user("acme", password="ancien-mdp-123", role=Role.CLIENT, partner=partner)
        self.client.force_login(user)
        resp = self.client.get(reverse("accounts:password_change"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "portal/base.html")
        resp = self.client.post(reverse("accounts:password_change"), {
            "old_password": "ancien-mdp-123", "new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD,
        })
        self.assertRedirects(resp, reverse("portal:home"), fetch_redirect_response=False)

    def test_wrong_old_password(self):
        user = User.objects.create_user("agent", password="ancien-mdp-123")
        self.client.force_login(user)
        resp = self.client.post(reverse("accounts:password_change"), {
            "old_password": "faux", "new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD,
        })
        self.assertEqual(resp.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password("ancien-mdp-123"))


class SendResetLinkTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("boss", password="x", role=Role.ADMIN)
        self.target = User.objects.create_user("nadia", email="nadia@acme.ma", password="x")

    def test_admin_sends_link_to_that_user_only(self):
        User.objects.create_user("homonyme", email="nadia@acme.ma", password="x")  # same address
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("accounts:team_list")), "Lien mot de passe")
        resp = self.client.post(reverse("accounts:send_reset_link", args=[self.target.pk]), follow=True)
        self.assertContains(resp, "Lien de réinitialisation envoyé à nadia@acme.ma")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("identifiant : nadia", mail.outbox[0].body)
        # and the link works for that user
        resp = self.client.get(reset_link(mail.outbox[0]), follow=True)
        self.assertTrue(resp.context["validlink"])

    def test_user_without_email(self):
        self.target.email = ""
        self.target.save()
        self.client.force_login(self.admin)
        resp = self.client.post(reverse("accounts:send_reset_link", args=[self.target.pk]), follow=True)
        self.assertContains(resp, "n&#x27;a pas d&#x27;adresse e-mail")
        self.assertEqual(mail.outbox, [])

    def test_non_admin_forbidden(self):
        self.client.force_login(User.objects.create_user("agent", password="x"))
        resp = self.client.post(reverse("accounts:send_reset_link", args=[self.target.pk]))
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(mail.outbox, [])
