from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse

from core.numbering import generate_reference
from dossiers.models import Dossier
from partners.models import Partner


class TypeFrais(models.TextChoices):
    HONORAIRES = "honoraires", "Honoraires de transit"
    DEBOURS = "debours", "Débours"
    DROITS_TAXES = "droits_taxes", "Droits et taxes"
    ACCONAGE = "acconage", "Acconage"
    MANUTENTION = "manutention", "Manutention"
    TRANSPORT = "transport", "Transport"
    AUTRE = "autre", "Autre"


class StatutDevis(models.TextChoices):
    BROUILLON = "brouillon", "Brouillon"
    ENVOYE = "envoye", "Envoyé"
    ACCEPTE = "accepte", "Accepté"
    REFUSE = "refuse", "Refusé"
    EXPIRE = "expire", "Expiré"


class TypeDevis(models.TextChoices):
    DEVIS = "devis", "Devis"
    PROFORMA = "proforma", "Facture proforma"


class Quote(models.Model):
    reference = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    type_devis = models.CharField(
        "Type", max_length=10, choices=TypeDevis.choices, default=TypeDevis.DEVIS
    )
    dossier = models.ForeignKey(
        Dossier, verbose_name="Dossier", on_delete=models.CASCADE, related_name="devis",
        null=True, blank=True,
    )
    client = models.ForeignKey(
        Partner, verbose_name="Client", on_delete=models.PROTECT, related_name="devis"
    )
    statut = models.CharField(
        "Statut", max_length=15, choices=StatutDevis.choices, default=StatutDevis.BROUILLON
    )
    date_creation = models.DateField("Date de création", auto_now_add=True)
    date_validite = models.DateField("Valide jusqu'au", null=True, blank=True)
    notes = models.TextField("Notes", blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Devis / Proforma"
        verbose_name_plural = "Devis & Proformas"

    def __str__(self):
        return f"{self.reference} - {self.client}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = generate_reference(Quote, "DV")
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("billing:quote_detail", kwargs={"pk": self.pk})

    @property
    def montant_total(self):
        return sum((line.montant for line in self.lignes.all()), Decimal("0"))


class QuoteLine(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="lignes")
    type_frais = models.CharField("Type de frais", max_length=20, choices=TypeFrais.choices)
    designation = models.CharField("Désignation", max_length=255)
    quantite = models.DecimalField("Quantité", max_digits=10, decimal_places=2, default=1)
    prix_unitaire = models.DecimalField("Prix unitaire", max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]

    @property
    def montant(self):
        return (self.quantite or Decimal("0")) * (self.prix_unitaire or Decimal("0"))

    def __str__(self):
        return self.designation


class StatutFacture(models.TextChoices):
    BROUILLON = "brouillon", "Brouillon"
    ENVOYEE = "envoyee", "Envoyée"
    PAYEE_PARTIEL = "payee_partiel", "Payée partiellement"
    PAYEE = "payee", "Payée"
    EN_RETARD = "en_retard", "En retard"
    ANNULEE = "annulee", "Annulée"


class Invoice(models.Model):
    reference = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    dossier = models.ForeignKey(
        Dossier, verbose_name="Dossier", on_delete=models.CASCADE, related_name="factures",
        null=True, blank=True,
    )
    client = models.ForeignKey(
        Partner, verbose_name="Client", on_delete=models.PROTECT, related_name="factures"
    )
    statut = models.CharField(
        "Statut", max_length=15, choices=StatutFacture.choices, default=StatutFacture.BROUILLON
    )
    date_emission = models.DateField("Date d'émission", auto_now_add=True)
    date_echeance = models.DateField("Date d'échéance", null=True, blank=True)
    notes = models.TextField("Notes / Note de détail", blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Facture"
        verbose_name_plural = "Factures"

    def __str__(self):
        return f"{self.reference} - {self.client}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = generate_reference(Invoice, "FA")
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("billing:invoice_detail", kwargs={"pk": self.pk})

    @property
    def montant_total(self):
        return sum((line.montant for line in self.lignes.all()), Decimal("0"))

    @property
    def montant_paye(self):
        return sum((p.montant for p in self.paiements.all()), Decimal("0"))

    @property
    def solde(self):
        return self.montant_total - self.montant_paye

    @property
    def is_impayee(self):
        return self.solde > 0 and self.statut not in (StatutFacture.ANNULEE,)


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lignes")
    type_frais = models.CharField("Type de frais", max_length=20, choices=TypeFrais.choices)
    designation = models.CharField("Désignation", max_length=255)
    quantite = models.DecimalField("Quantité", max_digits=10, decimal_places=2, default=1)
    prix_unitaire = models.DecimalField("Prix unitaire", max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]

    @property
    def montant(self):
        return (self.quantite or Decimal("0")) * (self.prix_unitaire or Decimal("0"))

    def __str__(self):
        return self.designation


class ModePaiement(models.TextChoices):
    ESPECES = "especes", "Espèces (caisse)"
    CHEQUE = "cheque", "Chèque"
    VIREMENT = "virement", "Virement"
    EFFET = "effet", "Effet de commerce"
    AUTRE = "autre", "Autre"


class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="paiements")
    montant = models.DecimalField("Montant", max_digits=14, decimal_places=2)
    date_paiement = models.DateField("Date de paiement")
    mode_paiement = models.CharField(
        "Mode de paiement", max_length=15, choices=ModePaiement.choices, default=ModePaiement.VIREMENT
    )
    reference = models.CharField("Référence (chèque, virement...)", max_length=100, blank=True)
    notes = models.CharField("Notes", max_length=255, blank=True)
    compte = models.ForeignKey(
        "treasury.CashAccount", verbose_name="Caisse / compte encaissé",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="encaissements",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_paiement"]
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"

    def __str__(self):
        return f"{self.montant} - {self.invoice.reference}"


class TypeRelance(models.TextChoices):
    EMAIL = "email", "Email"
    TELEPHONE = "telephone", "Téléphone"
    COURRIER = "courrier", "Courrier"
    VISITE = "visite", "Visite"


class Reminder(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="relances")
    type_relance = models.CharField("Type de relance", max_length=15, choices=TypeRelance.choices)
    date_relance = models.DateField("Date de la relance")
    notes = models.TextField("Compte-rendu", blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_relance"]
        verbose_name = "Relance"
        verbose_name_plural = "Relances"

    def __str__(self):
        return f"Relance {self.get_type_relance_display()} - {self.invoice.reference}"
