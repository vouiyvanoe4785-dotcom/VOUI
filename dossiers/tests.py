import datetime

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User
from partners.models import Partner, PartnerType

from .models import Dossier, StatutDossier, TypeOperation


class DossierReferenceTests(TestCase):
    def setUp(self):
        self.client_partner = Partner.objects.create(
            type_tiers=PartnerType.CLIENT, raison_sociale="Atlas Industries"
        )

    def test_reference_is_auto_generated(self):
        dossier = Dossier.objects.create(
            client=self.client_partner, type_operation=TypeOperation.IMPORT
        )
        year = datetime.date.today().year
        self.assertEqual(dossier.reference, f"AT-{year}-0001")

    def test_reference_increments_sequentially(self):
        d1 = Dossier.objects.create(client=self.client_partner, type_operation=TypeOperation.IMPORT)
        d2 = Dossier.objects.create(client=self.client_partner, type_operation=TypeOperation.EXPORT)
        year = datetime.date.today().year
        self.assertEqual(d1.reference, f"AT-{year}-0001")
        self.assertEqual(d2.reference, f"AT-{year}-0002")

    def test_reference_is_not_regenerated_on_save(self):
        dossier = Dossier.objects.create(
            client=self.client_partner, type_operation=TypeOperation.IMPORT
        )
        original_reference = dossier.reference
        dossier.statut = StatutDossier.EN_COURS
        dossier.save()
        dossier.refresh_from_db()
        self.assertEqual(dossier.reference, original_reference)


class DossierViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="agent", password="pass12345", role=Role.AGENT_TRANSIT
        )
        self.client_partner = Partner.objects.create(
            type_tiers=PartnerType.CLIENT, raison_sociale="Atlas Industries"
        )
        self.dossier = Dossier.objects.create(
            client=self.client_partner, type_operation=TypeOperation.IMPORT
        )

    def test_list_requires_login(self):
        response = self.client.get(reverse("dossiers:list"))
        self.assertEqual(response.status_code, 302)

    def test_detail_accessible_when_logged_in(self):
        self.client.login(username="agent", password="pass12345")
        response = self.client.get(reverse("dossiers:detail", kwargs={"pk": self.dossier.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.dossier.reference)

    def test_create_dossier_sets_created_by(self):
        self.client.login(username="agent", password="pass12345")
        response = self.client.post(
            reverse("dossiers:create"),
            {
                "client": self.client_partner.pk, "type_operation": TypeOperation.EXPORT,
                "statut": StatutDossier.OUVERT,
            },
        )
        self.assertEqual(response.status_code, 302)
        new_dossier = Dossier.objects.exclude(pk=self.dossier.pk).get()
        self.assertEqual(new_dossier.created_by, self.user)


class PaginationKeepsFiltersTests(TestCase):
    def test_next_page_link_keeps_filters(self):
        partner = Partner.objects.create(raison_sociale="ACME")
        for _ in range(25):
            Dossier.objects.create(client=partner, type_operation=TypeOperation.IMPORT, statut=StatutDossier.EN_DOUANE)
        self.client.force_login(User.objects.create_user("agent", password="x"))
        resp = self.client.get(reverse("dossiers:list"), {"statut": "en_douane", "q": "ACME"})
        self.assertContains(resp, 'href="?statut=en_douane&amp;q=ACME&amp;page=2"')
        page2 = self.client.get(reverse("dossiers:list"), {"statut": "en_douane", "q": "ACME", "page": 2})
        self.assertEqual(len(page2.context["dossiers"]), 5)
        self.assertContains(page2, 'href="?statut=en_douane&amp;q=ACME&amp;page=1"')
