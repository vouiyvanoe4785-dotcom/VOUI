from django.conf import settings
from django.db import models
from django.urls import reverse


class TypeCompte(models.TextChoices):
    CAISSE = "caisse", "Caisse (espèces)"
    BANQUE = "banque", "Compte bancaire"


class CashAccount(models.Model):
    nom = models.CharField("Nom du compte / de la caisse", max_length=150)
    type_compte = models.CharField(
        "Type", max_length=10, choices=TypeCompte.choices, default=TypeCompte.CAISSE
    )
    devise = models.CharField("Devise", max_length=10, default="MAD")
    solde_initial = models.DecimalField(
        "Solde initial", max_digits=14, decimal_places=2, default=0
    )
    numero_compte = models.CharField(
        "N° de compte bancaire (si applicable)", max_length=50, blank=True
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Responsable",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="caisses_gerees",
    )
    is_active = models.BooleanField("Actif", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nom"]
        verbose_name = "Caisse / Compte de trésorerie"
        verbose_name_plural = "Caisses & Comptes de trésorerie"

    def __str__(self):
        return f"{self.nom} ({self.get_type_compte_display()})"

    def get_absolute_url(self):
        return reverse("treasury:account_detail", kwargs={"pk": self.pk})

    @property
    def solde(self):
        agg = self.mouvements.aggregate(
            entrees=models.Sum("montant", filter=models.Q(type_mouvement=TypeMouvement.ENTREE)),
            sorties=models.Sum("montant", filter=models.Q(type_mouvement=TypeMouvement.SORTIE)),
        )
        entrees = agg["entrees"] or 0
        sorties = agg["sorties"] or 0
        return self.solde_initial + entrees - sorties


class TypeMouvement(models.TextChoices):
    ENTREE = "entree", "Entrée"
    SORTIE = "sortie", "Sortie"


class CategorieMouvement(models.TextChoices):
    ENCAISSEMENT_CLIENT = "encaissement_client", "Encaissement client"
    PAIEMENT_FOURNISSEUR = "paiement_fournisseur", "Paiement fournisseur / prestataire"
    DEBOURS_DOSSIER = "debours_dossier", "Débours pour un dossier (droits, taxes...)"
    FRAIS_GENERAUX = "frais_generaux", "Frais généraux"
    VIREMENT_INTERNE = "virement_interne", "Virement interne entre comptes"
    AUTRE = "autre", "Autre"


class CashTransaction(models.Model):
    compte = models.ForeignKey(
        CashAccount, verbose_name="Caisse / Compte", on_delete=models.CASCADE,
        related_name="mouvements",
    )
    type_mouvement = models.CharField(
        "Sens", max_length=10, choices=TypeMouvement.choices
    )
    categorie = models.CharField(
        "Catégorie", max_length=25, choices=CategorieMouvement.choices,
        default=CategorieMouvement.AUTRE,
    )
    montant = models.DecimalField("Montant", max_digits=14, decimal_places=2)
    date_mouvement = models.DateField("Date")
    description = models.CharField("Libellé", max_length=255, blank=True)

    dossier = models.ForeignKey(
        "dossiers.Dossier", verbose_name="Dossier lié", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="mouvements_caisse",
    )
    tiers = models.ForeignKey(
        "partners.Partner", verbose_name="Tiers (client / fournisseur)",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="mouvements_caisse",
    )
    related_payment = models.OneToOneField(
        "billing.Payment", verbose_name="Paiement de facture lié", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="mouvement_caisse",
    )
    transfer_ref = models.ForeignKey(
        "self", verbose_name="Mouvement de virement lié", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_mouvement", "-created_at"]
        verbose_name = "Mouvement de caisse"
        verbose_name_plural = "Mouvements de caisse"

    def __str__(self):
        signe = "+" if self.type_mouvement == TypeMouvement.ENTREE else "-"
        return f"{signe}{self.montant} {self.compte.devise} - {self.compte}"
