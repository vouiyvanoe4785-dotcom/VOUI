from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User

from .models import CashAccount, CashTransaction, TypeMouvement


class CashAccountSoldeTests(TestCase):
    def test_solde_defaults_to_initial_balance(self):
        account = CashAccount.objects.create(nom="Caisse", solde_initial=Decimal("1000"))
        self.assertEqual(account.solde, Decimal("1000"))

    def test_solde_reflects_entries_and_exits(self):
        account = CashAccount.objects.create(nom="Caisse", solde_initial=Decimal("1000"))
        CashTransaction.objects.create(
            compte=account, type_mouvement=TypeMouvement.ENTREE, montant=Decimal("500"),
            date_mouvement="2026-01-01",
        )
        CashTransaction.objects.create(
            compte=account, type_mouvement=TypeMouvement.SORTIE, montant=Decimal("200"),
            date_mouvement="2026-01-02",
        )
        self.assertEqual(account.solde, Decimal("1300"))


class TreasuryAccessControlTests(TestCase):
    def setUp(self):
        self.comptable = User.objects.create_user(
            username="compta", password="pass12345", role=Role.COMPTABLE
        )
        self.agent = User.objects.create_user(
            username="agent", password="pass12345", role=Role.AGENT_TRANSIT
        )

    def test_agent_cannot_access_account_list(self):
        self.client.login(username="agent", password="pass12345")
        response = self.client.get(reverse("treasury:account_list"))
        self.assertEqual(response.status_code, 403)

    def test_comptable_can_access_account_list(self):
        self.client.login(username="compta", password="pass12345")
        response = self.client.get(reverse("treasury:account_list"))
        self.assertEqual(response.status_code, 200)


class TransferCreateViewTests(TestCase):
    def setUp(self):
        self.comptable = User.objects.create_user(
            username="compta", password="pass12345", role=Role.COMPTABLE
        )
        self.source = CashAccount.objects.create(nom="Banque", solde_initial=Decimal("20000"))
        self.destination = CashAccount.objects.create(nom="Caisse", solde_initial=Decimal("5000"))

    def test_transfer_moves_money_between_accounts(self):
        self.client.login(username="compta", password="pass12345")
        response = self.client.post(
            reverse("treasury:transfer_create"),
            {
                "compte_source": self.source.pk, "compte_destination": self.destination.pk,
                "montant": "2000", "date_mouvement": "2026-01-01", "description": "Approvisionnement",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.source.refresh_from_db()
        self.destination.refresh_from_db()
        self.assertEqual(self.source.solde, Decimal("18000"))
        self.assertEqual(self.destination.solde, Decimal("7000"))

    def test_transfer_links_the_two_movements_together(self):
        self.client.login(username="compta", password="pass12345")
        self.client.post(
            reverse("treasury:transfer_create"),
            {
                "compte_source": self.source.pk, "compte_destination": self.destination.pk,
                "montant": "2000", "date_mouvement": "2026-01-01",
            },
        )
        sortie = self.source.mouvements.get()
        entree = self.destination.mouvements.get()
        self.assertEqual(sortie.transfer_ref, entree)
        self.assertEqual(entree.transfer_ref, sortie)

    def test_same_source_and_destination_is_rejected(self):
        self.client.login(username="compta", password="pass12345")
        response = self.client.post(
            reverse("treasury:transfer_create"),
            {
                "compte_source": self.source.pk, "compte_destination": self.source.pk,
                "montant": "100", "date_mouvement": "2026-01-01",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CashTransaction.objects.exists())
