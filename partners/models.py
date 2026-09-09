from django.db import models


class PartnerType(models.TextChoices):
    CLIENT = "client", "Client"
    FOURNISSEUR = "fournisseur", "Fournisseur"
    TRANSPORTEUR = "transporteur", "Transporteur"
    PRESTATAIRE = "prestataire", "Prestataire de service"
    DOUANE = "douane", "Agent en douane"
    BANQUE = "banque", "Banque / assurance"
    AUTRE = "autre", "Autre"


class Partner(models.Model):
    type_tiers = models.CharField(
        "Type de tiers", max_length=20, choices=PartnerType.choices, default=PartnerType.CLIENT
    )
    raison_sociale = models.CharField("Raison sociale", max_length=200)
    ice = models.CharField("ICE / N° d'identification", max_length=50, blank=True)
    rc = models.CharField("Registre de commerce", max_length=50, blank=True)
    contact_principal = models.CharField("Contact principal", max_length=150, blank=True)
    telephone = models.CharField("Téléphone", max_length=50, blank=True)
    email = models.EmailField("Email", blank=True)
    adresse = models.CharField("Adresse", max_length=255, blank=True)
    ville = models.CharField("Ville", max_length=100, blank=True)
    pays = models.CharField("Pays", max_length=100, default="Maroc")
    notes = models.TextField("Notes", blank=True)
    is_active = models.BooleanField("Actif", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["raison_sociale"]
        verbose_name = "Client / Tiers"
        verbose_name_plural = "Clients & Tiers"

    def __str__(self):
        return self.raison_sociale

    def get_type_badge(self):
        return self.get_type_tiers_display()
