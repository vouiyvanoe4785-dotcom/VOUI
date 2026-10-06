import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts.models import Role, User
from core.models import Societe
from dossiers.models import Dossier, TypeOperation
from partners.models import Partner, PartnerType

from .forms import DocumentForm
from .models import Document


class DocumentExtensionValidationTests(TestCase):
    """Regression tests for the unrestricted-file-upload / stored XSS fix."""

    def test_html_upload_is_rejected(self):
        malicious = SimpleUploadedFile(
            "malicious.html", b"<script>alert(document.cookie)</script>", content_type="text/html"
        )
        form = DocumentForm(
            data={"type_document": "autre", "libelle": "test"}, files={"fichier": malicious}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("fichier", form.errors)

    def test_svg_upload_is_rejected(self):
        malicious = SimpleUploadedFile(
            "image.svg", b"<svg onload='alert(1)'></svg>", content_type="image/svg+xml"
        )
        form = DocumentForm(
            data={"type_document": "autre", "libelle": "test"}, files={"fichier": malicious}
        )
        self.assertFalse(form.is_valid())

    def test_pdf_upload_is_accepted(self):
        good_file = SimpleUploadedFile(
            "facture.pdf", b"%PDF-1.4 fake pdf content", content_type="application/pdf"
        )
        form = DocumentForm(
            data={"type_document": "autre", "libelle": "test"}, files={"fichier": good_file}
        )
        self.assertTrue(form.is_valid(), form.errors)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class DocumentViewsTests(TestCase):
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

    def test_upload_requires_login(self):
        response = self.client.get(
            reverse("documents:create", kwargs={"dossier_pk": self.dossier.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_upload_sets_dossier_and_uploaded_by(self):
        self.client.login(username="agent", password="pass12345")
        good_file = SimpleUploadedFile(
            "facture.pdf", b"%PDF-1.4 fake pdf content", content_type="application/pdf"
        )
        response = self.client.post(
            reverse("documents:create", kwargs={"dossier_pk": self.dossier.pk}),
            {"type_document": "autre", "libelle": "Facture", "fichier": good_file},
        )
        self.assertEqual(response.status_code, 302)
        document = Document.objects.get()
        self.assertEqual(document.dossier, self.dossier)
        self.assertEqual(document.uploaded_by, self.user)

    def test_html_upload_rejected_end_to_end(self):
        self.client.login(username="agent", password="pass12345")
        malicious = SimpleUploadedFile(
            "malicious.html", b"<script>alert(1)</script>", content_type="text/html"
        )
        response = self.client.post(
            reverse("documents:create", kwargs={"dossier_pk": self.dossier.pk}),
            {"type_document": "autre", "libelle": "Pwn", "fichier": malicious},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Document.objects.exists())


class ProtectedFilesTests(TestCase):
    def setUp(self):
        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media)
        override.enable()
        self.addCleanup(override.disable)

        self.staff = User.objects.create_user("agent", password="x", role=Role.AGENT_TRANSIT)
        partner = Partner.objects.create(raison_sociale="ACME")
        self.dossier = Dossier.objects.create(client=partner, type_operation=TypeOperation.IMPORT)
        self.doc = Document.objects.create(
            dossier=self.dossier, type_document="dau",
            fichier=SimpleUploadedFile("dum.pdf", b"%PDF-1.4 DUM"),
        )
        self.url = reverse("documents:download", args=[self.doc.pk])

    def test_anonymous_is_sent_to_login(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].startswith(reverse("accounts:login")))

    def test_media_url_is_not_served(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get("/" + "media/" + self.doc.fichier.name).status_code, 404)

    def test_staff_download(self):
        self.client.force_login(self.staff)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(b"".join(resp.streaming_content), b"%PDF-1.4 DUM")
        self.assertIn('filename="dum.pdf"', resp["Content-Disposition"])

        page = self.client.get(self.dossier.get_absolute_url())
        self.assertContains(page, self.url)
        self.assertNotContains(page, "/media/")

    def test_missing_file_is_404(self):
        self.doc.fichier.delete(save=False)
        self.doc.fichier.name = "dossiers/x/documents/disparu.pdf"
        self.doc.save()
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    @override_settings(PROTECTED_MEDIA_ACCEL_PREFIX="/protected-media/")
    def test_nginx_x_accel_redirect(self):
        self.client.force_login(self.staff)
        resp = self.client.get(self.url)
        self.assertEqual(resp["X-Accel-Redirect"], "/protected-media/" + self.doc.fichier.name)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertEqual(resp.content, b"")

    def test_logo_is_public(self):
        self.assertEqual(self.client.get(reverse("core:logo")).status_code, 404)  # none uploaded yet
        buf = BytesIO()
        Image.new("RGB", (10, 10), "navy").save(buf, "PNG")
        societe = Societe.load()
        societe.logo = SimpleUploadedFile("logo.png", buf.getvalue(), content_type="image/png")
        societe.save()
        resp = self.client.get(reverse("core:logo"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "image/png")

        admin = User.objects.create_user("boss", password="x", role=Role.ADMIN)
        self.client.force_login(admin)
        form_page = self.client.get(reverse("core:societe"))
        self.assertContains(form_page, reverse("core:logo"))
        self.assertNotContains(form_page, "/media/")


class UploadExtensionTests(TestCase):
    def setUp(self):
        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media)
        override.enable()
        self.addCleanup(override.disable)
        self.client.force_login(User.objects.create_user("agent", password="x"))
        partner = Partner.objects.create(raison_sociale="ACME")
        self.dossier = Dossier.objects.create(client=partner, type_operation=TypeOperation.IMPORT)
        self.url = reverse("documents:create", args=[self.dossier.pk])

    def upload(self, name, content):
        return self.client.post(self.url, {
            "type_document": "autre", "fichier": SimpleUploadedFile(name, content),
        })

    def test_html_is_rejected(self):
        resp = self.upload("piege.html", b"<script>alert(1)</script>")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Document.objects.exists())
        self.assertContains(resp, "Formats acceptés")

    def test_pdf_is_accepted(self):
        resp = self.upload("bl.pdf", b"%PDF-1.4")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Document.objects.count(), 1)
