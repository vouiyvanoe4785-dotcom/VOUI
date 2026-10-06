from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from partners.models import Partner

from .models import Dossier, StatutDossier, TypeOperation


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
