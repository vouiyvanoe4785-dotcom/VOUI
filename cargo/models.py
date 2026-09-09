from django.db import models

from dossiers.models import Dossier


class Marchandise(models.Model):
    dossier = models.ForeignKey(
        Dossier, verbose_name="Dossier", on_delete=models.CASCADE, related_name="marchandises"
    )
    designation = models.CharField("Désignation", max_length=255)
    code_hs = models.CharField("Code SH / HS (indicatif)", max_length=20, blank=True)
    quantite = models.DecimalField("Quantité", max_digits=12, decimal_places=2, default=0)
    unite = models.CharField("Unité", max_length=20, default="colis")
    colisage = models.CharField("Colisage", max_length=100, blank=True)
    poids_brut = models.DecimalField(
        "Poids brut (kg)", max_digits=12, decimal_places=2, null=True, blank=True
    )
    poids_net = models.DecimalField(
        "Poids net (kg)", max_digits=12, decimal_places=2, null=True, blank=True
    )
    valeur = models.DecimalField(
        "Valeur déclarée", max_digits=14, decimal_places=2, null=True, blank=True
    )
    devise = models.CharField("Devise", max_length=10, default="MAD")
    origine = models.CharField("Pays d'origine", max_length=100, blank=True)
    notes = models.TextField("Notes", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "Marchandise / Cargo"
        verbose_name_plural = "Marchandises / Cargo"

    def __str__(self):
        return f"{self.designation} ({self.dossier.reference})"
