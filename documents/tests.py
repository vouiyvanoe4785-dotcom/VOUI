import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Role, User
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
