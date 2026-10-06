from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from billing.models import (
    DocumentTarifeMixin, LigneTarifeeMixin, ModePaiement, TauxTVA, TypeFrais,
)
from core.numbering import generate_reference
from dossiers.models import Dossier
from partners.models import Partner


class StatutAchat(models.TextChoices):
    BROUILLON = "brouillon", "Brouillon"
    RECUE = "recue", "Reçue"
    VALIDEE = "validee", "Validée"
    PAYEE_PARTIEL = "payee_partiel", "Payée partiellement"
    PAYEE = "payee", "Payée"
    CONTESTEE = "contestee", "Contestée"
    ANNULEE = "annulee", "Annulée"


# Taux proposé par défaut sur les achats, selon le type de frais (modifiable par ligne).
# Contrairement aux ventes, les débours facturés par un fournisseur (magasinage,
# manutention portuaire...) portent en général de la TVA ; seuls les droits et taxes
# payés à la douane n'en portent pas.
TAUX_TVA_ACHAT_PAR_FRAIS = {
    TypeFrais.HONORAIRES: TauxTVA.TAUX_20,
    TypeFrais.DEBOURS: TauxTVA.TAUX_20,
    TypeFrais.DROITS_TAXES: TauxTVA.EXONERE,
    TypeFrais.ACCONAGE: TauxTVA.TAUX_20,
    TypeFrais.MANUTENTION: TauxTVA.TAUX_20,
    TypeFrais.TRANSPORT: TauxTVA.TAUX_14,
    TypeFrais.AUTRE: TauxTVA.TAUX_20,
}


class SupplierInvoice(DocumentTarifeMixin, models.Model):
    reference = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    reference_fournisseur = models.CharField(
        "N° de facture fournisseur", max_length=100, blank=True
    )
    fournisseur = models.ForeignKey(
        Partner, verbose_name="Fournisseur / Prestataire", on_delete=models.PROTECT,
        related_name="achats",
    )
    dossier = models.ForeignKey(
        Dossier, verbose_name="Dossier", on_delete=models.CASCADE, related_name="achats",
        null=True, blank=True,
    )
    statut = models.CharField(
        "Statut", max_length=15, choices=StatutAchat.choices, default=StatutAchat.BROUILLON
    )
    date_facture = models.DateField("Date de la facture", default=timezone.localdate)
    date_echeance = models.DateField("Date d'échéance", null=True, blank=True)
    notes = models.TextField("Notes", blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Achat / Facture fournisseur"
        verbose_name_plural = "Achats & Factures fournisseurs"

    def __str__(self):
        return f"{self.reference} - {self.fournisseur}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = generate_reference(SupplierInvoice, "AC")
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("purchasing:invoice_detail", kwargs={"pk": self.pk})

    @property
    def est_exonere_tva(self):
        # The client exemption only applies to what we invoice; a supplier's VAT is
        # whatever the supplier charged.
        return False

    @property
    def montant_paye(self):
        return sum((p.montant for p in self.paiements.all()), Decimal("0"))

    @property
    def solde(self):
        return self.montant_total - self.montant_paye

    @property
    def is_impayee(self):
        return self.solde > 0 and self.statut not in (StatutAchat.ANNULEE,)


class SupplierInvoiceLine(LigneTarifeeMixin):
    invoice = models.ForeignKey(SupplierInvoice, on_delete=models.CASCADE, related_name="lignes")
    document_field = "invoice"

    class Meta(LigneTarifeeMixin.Meta):
        pass


class SupplierPayment(models.Model):
    invoice = models.ForeignKey(SupplierInvoice, on_delete=models.CASCADE, related_name="paiements")
    montant = models.DecimalField("Montant", max_digits=14, decimal_places=2)
    date_paiement = models.DateField("Date de paiement")
    mode_paiement = models.CharField(
        "Mode de paiement", max_length=15, choices=ModePaiement.choices, default=ModePaiement.VIREMENT
    )
    reference = models.CharField("Référence (chèque, virement...)", max_length=100, blank=True)
    compte = models.ForeignKey(
        "treasury.CashAccount", verbose_name="Caisse / compte débité",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="decaissements",
    )
    notes = models.CharField("Notes", max_length=255, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_paiement"]
        verbose_name = "Paiement fournisseur"
        verbose_name_plural = "Paiements fournisseurs"

    def __str__(self):
        return f"{self.montant} - {self.invoice.reference}"
