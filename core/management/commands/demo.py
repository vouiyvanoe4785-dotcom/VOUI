import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Role, User
from billing.models import Invoice, InvoiceLine, Payment, Quote, QuoteLine, StatutDevis, StatutFacture
from cargo.models import Marchandise
from core.models import Societe
from dossiers.models import Dossier, Incoterm, RegimeDouanier, StatutDossier, TypeOperation
from partners.models import Partner, PartnerType
from purchasing.models import StatutAchat, SupplierInvoice, SupplierInvoiceLine
from tracking.models import DossierEvent, TypeEvenement
from treasury.models import CashAccount, CashTransaction, CategorieMouvement, TypeCompte, TypeMouvement

DEMO_PASSWORD = "ayden2026"

DEMO_USERS = [
    ("admin", "Admin", "Ayden", Role.ADMIN, "Direction générale"),
    ("direction", "Yassine", "Alaoui", Role.DIRECTION, "Direction générale"),
    ("compta", "Sara", "Bennani", Role.COMPTABLE, "Comptabilité"),
    ("agent", "Nadia", "El Idrissi", Role.AGENT_TRANSIT, "Import"),
    ("agent2", "Omar", "Tazi", Role.AGENT_TRANSIT, "Export"),
]


class Command(BaseCommand):
    help = "Crée des comptes et des données de démonstration (sans effet si des dossiers existent déjà)."

    @transaction.atomic
    def handle(self, *args, **options):
        if Dossier.objects.exists():
            self.stdout.write("Des données existent déjà : rien n'a été ajouté.")
            return

        users = {}
        for username, first, last, role, service in DEMO_USERS:
            user = User.objects.filter(username=username).first()
            if user is None:
                user = User.objects.create_user(
                    username=username, password=DEMO_PASSWORD, first_name=first, last_name=last,
                    role=role, service=service, is_staff=role == Role.ADMIN,
                    is_superuser=role == Role.ADMIN,
                )
            users[username] = user

        societe = Societe.load()
        societe.raison_sociale = "Ayden Transit SARL"
        societe.adresse = "12, boulevard de la Corniche"
        societe.ville = "Casablanca"
        societe.telephone = "+212 5 22 00 00 00"
        societe.ice = "001234567000089"
        societe.rc = "123456"
        societe.save()

        atlas = Partner.objects.create(
            type_tiers=PartnerType.CLIENT, raison_sociale="Atlas Industries SARL",
            ice="001112223000045", contact_principal="Karim Benali", telephone="0522 33 44 55",
            email="karim@atlas-industries.ma", ville="Casablanca",
        )
        medtex = Partner.objects.create(
            type_tiers=PartnerType.CLIENT, raison_sociale="Medtex Export", contact_principal="Leila Fassi",
            telephone="0539 11 22 33", ville="Tanger",
        )
        zone_franche = Partner.objects.create(
            type_tiers=PartnerType.CLIENT, raison_sociale="Tanger Auto Components (zone franche)",
            ville="Tanger", exonere_tva=True, motif_exoneration="Zone franche - attestation n° ZF-2026-118",
        )
        maersk = Partner.objects.create(
            type_tiers=PartnerType.TRANSPORTEUR, raison_sociale="Maersk Line Maroc", ville="Casablanca",
        )
        marsa = Partner.objects.create(
            type_tiers=PartnerType.PRESTATAIRE, raison_sociale="Marsa Maroc (acconage)", ville="Casablanca",
        )

        client_user = User.objects.filter(username="client").first()
        if client_user is None:
            User.objects.create_user(
                username="client", password=DEMO_PASSWORD, first_name="Karim", last_name="Benali",
                role=Role.CLIENT, partner=atlas,
            )

        agent, agent2 = users["agent"], users["agent2"]

        d1 = Dossier.objects.create(
            client=atlas, reference_client="PO-2026-991", donneur_ordre="Atlas Industries SARL",
            type_operation=TypeOperation.IMPORT, regime_douanier=RegimeDouanier.MISE_CONSOMMATION,
            incoterm=Incoterm.CIF, origine="Chine", provenance="Shanghai", destination="Casablanca",
            agent_responsable=agent, statut=StatutDossier.EN_DOUANE, created_by=agent,
        )
        d2 = Dossier.objects.create(
            client=medtex, reference_client="EXP-4471", type_operation=TypeOperation.EXPORT,
            regime_douanier=RegimeDouanier.EXPORTATION_DEFINITIVE, incoterm=Incoterm.FOB,
            origine="Maroc", provenance="Tanger Med", destination="Marseille",
            agent_responsable=agent2, statut=StatutDossier.EN_COURS, created_by=agent2,
        )
        d3 = Dossier.objects.create(
            client=zone_franche, type_operation=TypeOperation.IMPORT,
            regime_douanier=RegimeDouanier.ADMISSION_TEMPORAIRE, incoterm=Incoterm.DAP,
            origine="Espagne", provenance="Algésiras", destination="Tanger Free Zone",
            agent_responsable=agent2, statut=StatutDossier.OUVERT, created_by=agent2,
        )
        d4 = Dossier.objects.create(
            client=atlas, type_operation=TypeOperation.IMPORT, origine="Turquie", provenance="Istanbul",
            destination="Casablanca", agent_responsable=agent, statut=StatutDossier.LIVRE, created_by=agent,
        )

        Marchandise.objects.create(
            dossier=d1, designation="Roulements à billes industriels", code_hs="8482.10", quantite=120,
            unite="colis", poids_brut=3400, valeur=250000, origine="Chine",
        )
        Marchandise.objects.create(
            dossier=d2, designation="Vêtements en coton", code_hs="6109.10", quantite=850,
            unite="cartons", poids_brut=6200, valeur=410000, origine="Maroc",
        )
        Marchandise.objects.create(
            dossier=d3, designation="Faisceaux électriques", code_hs="8544.30", quantite=40,
            unite="palettes", poids_brut=9800, valeur=780000, origine="Espagne",
        )

        now = timezone.now()
        for days_ago, type_evt, lieu, commentaire in (
            (6, TypeEvenement.ETA, "Port de Casablanca", "ETA communiquée par l'armateur"),
            (3, TypeEvenement.ARRIVEE, "Port de Casablanca", "Navire MSC Aurora à quai"),
            (2, TypeEvenement.DECLARATION, "Douane Casablanca port", "DUM déposée"),
            (1, TypeEvenement.VISITE, "Magasin cale 3", "Visite physique programmée"),
        ):
            DossierEvent.objects.create(
                dossier=d1, type_evenement=type_evt, lieu=lieu, commentaire=commentaire,
                date_evenement=now - datetime.timedelta(days=days_ago), created_by=agent,
            )

        devis = Quote.objects.create(
            client=medtex, dossier=d2, statut=StatutDevis.ENVOYE, created_by=agent2,
            date_validite=timezone.localdate() + datetime.timedelta(days=15),
        )
        for type_frais, designation, pu, taux in (
            ("honoraires", "Honoraires de transit export", "3500", 20),
            ("transport", "Transport Tanger - Tanger Med", "2200", 14),
            ("debours", "Frais portuaires (débours)", "1800", 0),
        ):
            QuoteLine.objects.create(quote=devis, type_frais=type_frais, designation=designation,
                                     prix_unitaire=pu, taux_tva=taux)

        facture1 = Invoice.objects.create(
            client=atlas, dossier=d1, statut=StatutFacture.ENVOYEE, created_by=users["compta"],
            date_echeance=timezone.localdate() + datetime.timedelta(days=30),
        )
        for type_frais, designation, pu, taux in (
            ("honoraires", "Honoraires de transit", "4500", 20),
            ("acconage", "Acconage", "1200", 20),
            ("manutention", "Manutention", "800", 20),
            ("droits_taxes", "Droits et taxes de douane", "18500", 0),
        ):
            InvoiceLine.objects.create(invoice=facture1, type_frais=type_frais, designation=designation,
                                       prix_unitaire=pu, taux_tva=taux)

        facture2 = Invoice.objects.create(
            client=atlas, dossier=d4, statut=StatutFacture.PAYEE_PARTIEL, created_by=users["compta"],
            date_echeance=timezone.localdate() - datetime.timedelta(days=12),
        )
        InvoiceLine.objects.create(invoice=facture2, type_frais="honoraires", designation="Honoraires de transit",
                                   prix_unitaire="5000", taux_tva=20)

        banque = CashAccount.objects.create(
            nom="Compte BMCE", type_compte=TypeCompte.BANQUE, solde_initial=Decimal("150000"),
            numero_compte="011 780 0000123456789 01", responsable=users["compta"],
        )
        CashAccount.objects.create(
            nom="Caisse espèces siège", type_compte=TypeCompte.CAISSE, solde_initial=Decimal("8000"),
            responsable=users["compta"],
        )
        paiement = Payment.objects.create(
            invoice=facture2, montant=Decimal("2000"), date_paiement=timezone.localdate(),
            mode_paiement="virement", reference="VIR-2026-0042", compte=banque, created_by=users["compta"],
        )
        CashTransaction.objects.create(
            compte=banque, type_mouvement=TypeMouvement.ENTREE, categorie=CategorieMouvement.ENCAISSEMENT_CLIENT,
            montant=paiement.montant, date_mouvement=paiement.date_paiement,
            description=f"Encaissement facture {facture2.reference} - {atlas}", dossier=d4, tiers=atlas,
            related_payment=paiement, created_by=users["compta"],
        )

        achat = SupplierInvoice.objects.create(
            fournisseur=marsa, dossier=d1, reference_fournisseur="MM-77812", statut=StatutAchat.RECUE,
            date_echeance=timezone.localdate() + datetime.timedelta(days=20), created_by=users["compta"],
        )
        SupplierInvoiceLine.objects.create(invoice=achat, type_frais="acconage", designation="Acconage conteneur 40'",
                                           prix_unitaire="950", taux_tva=20)
        achat2 = SupplierInvoice.objects.create(
            fournisseur=maersk, dossier=d1, reference_fournisseur="MAEU-55120", statut=StatutAchat.VALIDEE,
            created_by=users["compta"],
        )
        SupplierInvoiceLine.objects.create(invoice=achat2, type_frais="transport", designation="Fret maritime",
                                           prix_unitaire="14000", taux_tva=14)

        self.stdout.write(self.style.SUCCESS("Données de démonstration créées."))
        self.stdout.write(f"Comptes (mot de passe pour tous : {DEMO_PASSWORD}) :")
        for username, first, last, role, _ in DEMO_USERS:
            self.stdout.write(f"  {username:<10} {Role(role).label}")
        self.stdout.write(f"  {'client':<10} {Role.CLIENT.label} (Atlas Industries)")
