import shutil
import tempfile
from decimal import Decimal
from io import BytesIO, StringIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from pypdf import PdfReader

from accounts.models import Role, User

from .amounts import montant_en_lettres
from .models import Societe
from .pdf import render_pdf


class MontantEnLettresTests(TestCase):
    def test_conversions(self):
        cases = {
            "0": "zéro dirham",
            "1": "un dirham",
            "200": "deux cents dirhams",
            "1250.50": "mille deux cent cinquante dirhams et cinquante centimes",
            "80.01": "quatre-vingts dirhams et un centime",
            "1000000": "un million de dirhams",
            "1000200": "un million deux cents dirhams",
            "-15": "moins quinze dirhams",
        }
        for montant, attendu in cases.items():
            self.assertEqual(montant_en_lettres(Decimal(montant)), attendu, montant)

    def test_rounds_to_centimes(self):
        self.assertEqual(montant_en_lettres("9.999"), "dix dirhams")

    def test_other_currency(self):
        self.assertEqual(montant_en_lettres("2.5", "EUR"), "deux euros et cinquante centimes")


class SocieteTests(TestCase):
    def test_singleton(self):
        Societe.load()
        Societe(raison_sociale="Autre").save()
        self.assertEqual(Societe.objects.count(), 1)
        self.assertEqual(Societe.load().raison_sociale, "Autre")

    def test_mentions_legales_skip_empty(self):
        societe = Societe(ice="123", rc="", identifiant_fiscal="456")
        self.assertEqual(societe.mentions_legales, "ICE : 123 - IF : 456")

    def test_edit_page_admin_only(self):
        url = reverse("core:societe")
        self.client.force_login(User.objects.create_user("agent", password="x", role=Role.AGENT_TRANSIT))
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_login(User.objects.create_user("boss", password="x", role=Role.ADMIN))
        self.assertEqual(self.client.get(url).status_code, 200)
        resp = self.client.post(url, {"raison_sociale": "Ayden Transit SARL", "pays": "Maroc", "ice": "0011"})
        self.assertRedirects(resp, url)
        self.assertEqual(Societe.load().ice, "0011")


class RenderPdfTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)

    def test_logo_is_embedded(self):
        buf = BytesIO()
        Image.new("RGB", (40, 20), "navy").save(buf, "PNG")
        with override_settings(MEDIA_ROOT=self.media):
            societe = Societe.load()
            societe.logo = SimpleUploadedFile("logo.png", buf.getvalue(), content_type="image/png")
            societe.save()
            sans_logo = render_pdf("billing/pdf/document.html", {"societe": Societe(), "doc": {}, "client": {}})
            avec_logo = render_pdf("billing/pdf/document.html", {"societe": societe, "doc": {}, "client": {}})
        def images(content):
            return sum(len(page.images) for page in PdfReader(BytesIO(content)).pages)

        self.assertEqual(images(avec_logo), 1)
        self.assertEqual(images(sans_logo), 0)


class DemoCommandTests(TestCase):
    def test_creates_data_and_is_idempotent(self):
        from django.core.management import call_command

        from dossiers.models import Dossier

        call_command("demo", stdout=StringIO())
        nb = Dossier.objects.count()
        self.assertGreater(nb, 0)
        self.assertTrue(self.client.login(username="admin", password="ayden2026"))
        self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 200)

        call_command("demo", stdout=StringIO())
        self.assertEqual(Dossier.objects.count(), nb)


class EnsureAdminCommandTests(TestCase):
    def run_cmd(self, **env):
        import os
        from unittest import mock

        from django.core.management import call_command

        with mock.patch.dict(os.environ, env):
            call_command("ensure_admin", stdout=StringIO())

    def test_creates_admin_from_environment_once(self):
        self.run_cmd(ADMIN_PASSWORD="Un-Mot-De-Passe-Solide")
        admin = User.objects.get(username="admin")
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.role, Role.ADMIN)
        self.assertTrue(admin.check_password("Un-Mot-De-Passe-Solide"))

        # Later restarts must not reset a password the admin changed since.
        admin.set_password("Change-Depuis-Le-Menu")
        admin.save()
        self.run_cmd(ADMIN_PASSWORD="Un-Mot-De-Passe-Solide")
        admin.refresh_from_db()
        self.assertTrue(admin.check_password("Change-Depuis-Le-Menu"))

    def test_refuses_missing_or_short_password(self):
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            self.run_cmd(ADMIN_PASSWORD="")
        with self.assertRaises(CommandError):
            self.run_cmd(ADMIN_PASSWORD="court")
        self.assertFalse(User.objects.exists())
