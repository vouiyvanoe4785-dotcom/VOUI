from django.db import models


def logo_upload_path(instance, filename):
    return f"societe/{filename}"


class Societe(models.Model):
    """Company profile printed on quotes and invoices (single row, pk=1)."""

    raison_sociale = models.CharField("Raison sociale", max_length=200, default="Ayden Transit")
    activite = models.CharField(
        "Activité", max_length=200, blank=True,
        default="Transit - Dédouanement - Logistique",
    )
    adresse = models.CharField("Adresse", max_length=255, blank=True)
    ville = models.CharField("Ville", max_length=100, blank=True)
    pays = models.CharField("Pays", max_length=100, default="Maroc")
    telephone = models.CharField("Téléphone", max_length=50, blank=True)
    email = models.EmailField("Email", blank=True)
    site_web = models.CharField("Site web", max_length=150, blank=True)

    ice = models.CharField("ICE", max_length=50, blank=True)
    rc = models.CharField("Registre de commerce (RC)", max_length=50, blank=True)
    identifiant_fiscal = models.CharField("Identifiant fiscal (IF)", max_length=50, blank=True)
    patente = models.CharField("Patente / TP", max_length=50, blank=True)
    cnss = models.CharField("CNSS", max_length=50, blank=True)
    capital = models.CharField("Capital social", max_length=50, blank=True)

    banque = models.CharField("Banque", max_length=150, blank=True)
    rib = models.CharField("RIB", max_length=60, blank=True)

    logo = models.ImageField("Logo", upload_to=logo_upload_path, blank=True)
    mentions_facture = models.TextField(
        "Mentions en bas des factures", blank=True,
        help_text="Conditions de paiement, pénalités de retard, etc.",
    )
    mentions_devis = models.TextField(
        "Mentions en bas des devis", blank=True,
        help_text="Durée de validité, conditions d'acceptation, etc.",
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Société"
        verbose_name_plural = "Société"

    def __str__(self):
        return self.raison_sociale

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def mentions_legales(self):
        parts = [
            (label, value) for label, value in (
                ("ICE", self.ice), ("RC", self.rc), ("IF", self.identifiant_fiscal),
                ("Patente", self.patente), ("CNSS", self.cnss), ("Capital", self.capital),
            ) if value
        ]
        return " - ".join(f"{label} : {value}" for label, value in parts)
