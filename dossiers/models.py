from django.conf import settings
from django.db import models
from django.urls import reverse

from core.numbering import generate_reference
from partners.models import Partner


class TypeOperation(models.TextChoices):
    IMPORT = "import", "Import"
    EXPORT = "export", "Export"
    TRANSIT = "transit", "Transit"
    DOUANE = "douane", "Dédouanement"


class RegimeDouanier(models.TextChoices):
    MISE_CONSOMMATION = "mise_consommation", "Mise à la consommation"
    ADMISSION_TEMPORAIRE = "admission_temporaire", "Admission temporaire"
    EXPORTATION_DEFINITIVE = "exportation_definitive", "Exportation définitive"
    ENTREPOT_DOUANIER = "entrepot_douanier", "Entrepôt douanier"
    TRANSIT_DOUANIER = "transit_douanier", "Transit douanier"
    DRAWBACK = "drawback", "Drawback"
    AUTRE = "autre", "Autre"


class Incoterm(models.TextChoices):
    EXW = "EXW", "EXW - Ex Works"
    FCA = "FCA", "FCA - Free Carrier"
    FAS = "FAS", "FAS - Free Alongside Ship"
    FOB = "FOB", "FOB - Free On Board"
    CFR = "CFR", "CFR - Cost and Freight"
    CIF = "CIF", "CIF - Cost, Insurance and Freight"
    CPT = "CPT", "CPT - Carriage Paid To"
    CIP = "CIP", "CIP - Carriage and Insurance Paid To"
    DAP = "DAP", "DAP - Delivered At Place"
    DPU = "DPU", "DPU - Delivered at Place Unloaded"
    DDP = "DDP", "DDP - Delivered Duty Paid"


class StatutDossier(models.TextChoices):
    OUVERT = "ouvert", "Ouvert"
    EN_COURS = "en_cours", "En cours"
    EN_DOUANE = "en_douane", "En douane"
    LIVRE = "livre", "Livré"
    CLOTURE = "cloture", "Clôturé"
    ANNULE = "annule", "Annulé"


class Dossier(models.Model):
    reference = models.CharField(
        "N° de dossier", max_length=30, unique=True, blank=True, editable=False
    )
    reference_client = models.CharField("Référence client", max_length=100, blank=True)
    donneur_ordre = models.CharField("Donneur d'ordre", max_length=200, blank=True)

    client = models.ForeignKey(
        Partner, verbose_name="Client", on_delete=models.PROTECT, related_name="dossiers"
    )
    type_operation = models.CharField(
        "Type d'opération", max_length=20, choices=TypeOperation.choices
    )
    regime_douanier = models.CharField(
        "Régime douanier", max_length=30, choices=RegimeDouanier.choices, blank=True
    )
    incoterm = models.CharField("Incoterm", max_length=5, choices=Incoterm.choices, blank=True)

    origine = models.CharField("Origine", max_length=150, blank=True)
    provenance = models.CharField("Provenance", max_length=150, blank=True)
    destination = models.CharField("Destination", max_length=150, blank=True)

    agent_responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Agent responsable",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dossiers_geres",
    )

    statut = models.CharField(
        "Statut", max_length=20, choices=StatutDossier.choices, default=StatutDossier.OUVERT
    )
    date_ouverture = models.DateField("Date d'ouverture", auto_now_add=True)
    date_cloture = models.DateField("Date de clôture", null=True, blank=True)

    valide = models.BooleanField("Validé", default=False)
    valide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Validé par",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dossiers_valides",
    )
    valide_le = models.DateTimeField("Validé le", null=True, blank=True)

    notes = models.TextField("Notes", blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dossiers_crees",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Dossier de transit"
        verbose_name_plural = "Dossiers de transit"

    def __str__(self):
        return f"{self.reference} - {self.client}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = generate_reference(Dossier, "AT")
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("dossiers:detail", kwargs={"pk": self.pk})

    @property
    def is_cloture(self):
        return self.statut in (StatutDossier.CLOTURE, StatutDossier.ANNULE)
