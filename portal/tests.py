import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import URLPattern, URLResolver, get_resolver, reverse

from accounts.forms import UserCreateForm
from accounts.models import Role, User
from billing.models import Invoice, InvoiceLine, Quote, QuoteLine, StatutDevis, StatutFacture
from documents.models import Document
from dossiers.models import Dossier, TypeOperation
from partners.models import Partner
from tracking.models import DossierEvent, TypeEvenement


def iter_named_urls(resolver=None, namespace=""):
    """Yield (name, pattern) for every named URL of the project."""
    resolver = resolver or get_resolver()
    for entry in resolver.url_patterns:
        if isinstance(entry, URLResolver):
            ns = f"{namespace}{entry.namespace}:" if entry.namespace else namespace
            yield from iter_named_urls(entry, ns)
        elif isinstance(entry, URLPattern) and entry.name:
            yield f"{namespace}{entry.name}", entry.pattern


class PortalTestCase(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=self.media)
        override.enable()
        self.addCleanup(override.disable)

        self.acme = Partner.objects.create(raison_sociale="ACME Import")
        self.other = Partner.objects.create(raison_sociale="Concurrent SARL")
        self.client_user = User.objects.create_user(
            "acme", password="x", role=Role.CLIENT, partner=self.acme, first_name="Nadia"
        )
        self.staff = User.objects.create_user("agent", password="x", role=Role.AGENT_TRANSIT)

        self.dossier = Dossier.objects.create(
            client=self.acme, type_operation=TypeOperation.IMPORT, reference_client="PO-1"
        )
        self.other_dossier = Dossier.objects.create(client=self.other, type_operation=TypeOperation.EXPORT)

        self.invoice = self._invoice(self.acme, StatutFacture.ENVOYEE)
        self.draft = self._invoice(self.acme, StatutFacture.BROUILLON)
        self.other_invoice = self._invoice(self.other, StatutFacture.ENVOYEE)
        self.quote = Quote.objects.create(client=self.acme, dossier=self.dossier, statut=StatutDevis.ENVOYE)
        QuoteLine.objects.create(quote=self.quote, type_frais="honoraires", designation="H", prix_unitaire="100")
        self.draft_quote = Quote.objects.create(client=self.acme, statut=StatutDevis.BROUILLON)

        self.doc = Document.objects.create(
            dossier=self.dossier, type_document="connaissement",
            fichier=SimpleUploadedFile("bl.pdf", b"%PDF-1.4 B/L ACME"),
        )
        self.other_doc = Document.objects.create(
            dossier=self.other_dossier, type_document="connaissement",
            fichier=SimpleUploadedFile("bl-other.pdf", b"%PDF-1.4 secret"),
        )

    def _invoice(self, partner, statut):
        dossier = self.dossier if partner == self.acme else self.other_dossier
        invoice = Invoice.objects.create(client=partner, dossier=dossier, statut=statut)
        InvoiceLine.objects.create(invoice=invoice, type_frais="honoraires", designation="H", prix_unitaire="1000")
        return invoice


class PortalIsolationTests(PortalTestCase):
    def test_client_is_kept_out_of_every_staff_url(self):
        self.client.force_login(self.client_user)
        portal_home = reverse("portal:home")
        checked = 0
        for name, pattern in iter_named_urls():
            # Django admin URLs take non-numeric arguments; "/admin/" is checked below.
            if name.startswith(("portal:", "admin:")) or name in ("accounts:logout", "core:logo"):
                continue
            kwargs = {key: 1 for key in pattern.regex.groupindex}
            url = reverse(name, kwargs=kwargs)
            for method in (self.client.get, self.client.post):
                resp = method(url)
                self.assertEqual(resp.status_code, 302, f"{name} {url}")
                self.assertEqual(resp["Location"], portal_home, f"{name} {url}")
            checked += 1
        self.assertGreater(checked, 40)
        # Django admin too
        self.assertRedirects(self.client.get("/admin/"), portal_home, fetch_redirect_response=False)

    def test_staff_cannot_use_portal(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse("portal:home"))
        self.assertRedirects(resp, reverse("dashboard:home"), fetch_redirect_response=False)

    def test_client_without_company_is_refused(self):
        orphan = User.objects.create_user("orphan", password="x", role=Role.CLIENT)
        self.client.force_login(orphan)
        self.assertEqual(self.client.get(reverse("portal:home")).status_code, 403)

    def test_login_lands_on_portal(self):
        resp = self.client.post(reverse("accounts:login"), {"username": "acme", "password": "x"}, follow=True)
        self.assertEqual(resp.request["PATH_INFO"], reverse("portal:home"))
        self.assertContains(resp, "Bonjour Nadia")

    def test_other_clients_data_is_not_reachable(self):
        self.client.force_login(self.client_user)
        for url in (
            reverse("portal:dossier_detail", args=[self.other_dossier.pk]),
            reverse("portal:document_download", args=[self.other_doc.pk]),
            reverse("portal:invoice_pdf", args=[self.other_invoice.pk]),
            reverse("portal:invoice_pdf", args=[self.draft.pk]),
            reverse("portal:quote_pdf", args=[self.draft_quote.pk]),
        ):
            self.assertEqual(self.client.get(url).status_code, 404, url)

        listing = self.client.get(reverse("portal:dossier_list"))
        self.assertContains(listing, self.dossier.reference)
        self.assertNotContains(listing, self.other_dossier.reference)
        invoices = self.client.get(reverse("portal:invoice_list"))
        self.assertContains(invoices, self.invoice.reference)
        self.assertNotContains(invoices, self.draft.reference)
        self.assertNotContains(invoices, self.other_invoice.reference)
        quotes = self.client.get(reverse("portal:quote_list"))
        self.assertContains(quotes, self.quote.reference)
        self.assertNotContains(quotes, self.draft_quote.reference)


class PortalContentTests(PortalTestCase):
    def test_home(self):
        self.client.force_login(self.client_user)
        resp = self.client.get(reverse("portal:home"))
        self.assertEqual(resp.context["solde_du"], self.invoice.montant_total)  # draft excluded
        self.assertContains(resp, self.dossier.reference)
        self.assertNotContains(resp, "Équipe")  # no staff navigation
        # The logo is the only shared URL a client account may load (portal header).
        self.assertEqual(self.client.get(reverse("core:logo")).status_code, 404)  # not redirected

    def test_dossier_timeline_hides_internal_events(self):
        DossierEvent.objects.create(dossier=self.dossier, type_evenement=TypeEvenement.ARRIVEE, commentaire="Navire à quai")
        DossierEvent.objects.create(
            dossier=self.dossier, type_evenement=TypeEvenement.NOTE, commentaire="Client difficile", visible_client=True
        )
        DossierEvent.objects.create(dossier=self.dossier, type_evenement=TypeEvenement.INCIDENT,
                                    commentaire="Erreur de déclaration", visible_client=False)
        self.client.force_login(self.client_user)
        resp = self.client.get(reverse("portal:dossier_detail", args=[self.dossier.pk]))
        self.assertContains(resp, "Navire à quai")
        self.assertNotContains(resp, "Client difficile")   # notes are forced internal
        self.assertNotContains(resp, "Erreur de déclaration")
        self.assertContains(resp, self.invoice.reference)
        self.assertNotContains(resp, self.draft.reference)

    def test_document_download(self):
        self.client.force_login(self.client_user)
        resp = self.client.get(reverse("portal:document_download", args=[self.doc.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(b"".join(resp.streaming_content), b"%PDF-1.4 B/L ACME")
        self.assertIn("attachment", resp["Content-Disposition"])

    def test_pdfs(self):
        self.client.force_login(self.client_user)
        for url in (
            reverse("portal:invoice_pdf", args=[self.invoice.pk]),
            reverse("portal:quote_pdf", args=[self.quote.pk]),
        ):
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, url)
            self.assertEqual(resp["Content-Type"], "application/pdf")


class PortalAccountTests(TestCase):
    def setUp(self):
        self.acme = Partner.objects.create(raison_sociale="ACME Import")

    def form(self, **extra):
        data = {"username": "nadia", "password1": "Un-mot-de-passe-solide-42", "password2": "Un-mot-de-passe-solide-42"}
        data.update(extra)
        return UserCreateForm(data=data)

    def test_client_role_requires_company(self):
        form = self.form(role=Role.CLIENT)
        self.assertFalse(form.is_valid())
        self.assertIn("partner", form.errors)
        self.assertTrue(self.form(role=Role.CLIENT, partner=self.acme.pk).is_valid())

    def test_staff_role_drops_company(self):
        form = self.form(role=Role.AGENT_TRANSIT, partner=self.acme.pk)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.save().partner)

    def test_admin_creates_access_from_client_page(self):
        admin = User.objects.create_user("boss", password="x", role=Role.ADMIN)
        self.client.force_login(admin)
        page = self.client.get(reverse("partners:detail", args=[self.acme.pk]))
        self.assertContains(page, "Accès au portail client")
        url = reverse("accounts:team_create") + f"?role=client&partner={self.acme.pk}"
        form_page = self.client.get(url)
        self.assertEqual(form_page.context["form"].initial["partner"], str(self.acme.pk))
        resp = self.client.post(reverse("accounts:team_create"), {
            "username": "nadia", "role": Role.CLIENT, "partner": self.acme.pk,
            "password1": "Un-mot-de-passe-solide-42", "password2": "Un-mot-de-passe-solide-42",
        })
        self.assertRedirects(resp, reverse("partners:detail", args=[self.acme.pk]), fetch_redirect_response=False)
        self.assertEqual(User.objects.get(username="nadia").partner, self.acme)
