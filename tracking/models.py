from django.conf import settings
from django.db import models
from django.utils import timezone

from dossiers.models import Dossier, StatutDossier


class TypeEvenement(models.TextChoices):
    CHANGEMENT_STATUT = "changement_statut", "Changement de statut"
    ETA = "eta", "ETA communiquée"
    ARRIVEE = "arrivee", "Arrivée navire / avion / camion"
    DECHARGEMENT = "dechargement", "Déchargement / mise en magasin"
    DECLARATION = "declaration", "Déclaration en douane déposée"
    VISITE = "visite", "Visite / contrôle douanier"
    LIQUIDATION = "liquidation", "Droits et taxes liquidés"
    BAE = "bae", "Bon à enlever (BAE) obtenu"
    ENLEVEMENT = "enlevement", "Enlèvement de la marchandise"
    LIVRAISON = "livraison", "Livraison au client"
    INCIDENT = "incident", "Incident / blocage"
    NOTE = "note", "Note interne"
    AUTRE = "autre", "Autre"


EVENT_ICONS = {
    TypeEvenement.CHANGEMENT_STATUT: "arrow-repeat",
    TypeEvenement.ETA: "clock",
    TypeEvenement.ARRIVEE: "geo-alt",
    TypeEvenement.DECHARGEMENT: "box-seam",
    TypeEvenement.DECLARATION: "file-earmark-text",
    TypeEvenement.VISITE: "search",
    TypeEvenement.LIQUIDATION: "cash-coin",
    TypeEvenement.BAE: "patch-check",
    TypeEvenement.ENLEVEMENT: "truck",
    TypeEvenement.LIVRAISON: "house-check",
    TypeEvenement.INCIDENT: "exclamation-triangle",
    TypeEvenement.NOTE: "chat-left-text",
    TypeEvenement.AUTRE: "dot",
}


class DossierEvent(models.Model):
    dossier = models.ForeignKey(
        Dossier, verbose_name="Dossier", on_delete=models.CASCADE, related_name="evenements"
    )
    type_evenement = models.CharField(
        "Type d'événement", max_length=30, choices=TypeEvenement.choices
    )
    date_evenement = models.DateTimeField("Date de l'événement", default=timezone.now)
    lieu = models.CharField("Lieu", max_length=150, blank=True)
    commentaire = models.TextField("Commentaire", blank=True)

    ancien_statut = models.CharField(
        "Ancien statut", max_length=20, choices=StatutDossier.choices, blank=True
    )
    nouveau_statut = models.CharField(
        "Nouveau statut", max_length=20, choices=StatutDossier.choices, blank=True
    )
    automatique = models.BooleanField("Généré automatiquement", default=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="evenements_dossier",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_evenement", "-created_at"]
        verbose_name = "Événement de suivi"
        verbose_name_plural = "Événements de suivi"

    def __str__(self):
        return f"{self.dossier.reference} - {self.get_type_evenement_display()}"

    @property
    def icon(self):
        return EVENT_ICONS.get(self.type_evenement, "dot")

    @property
    def is_incident(self):
        return self.type_evenement == TypeEvenement.INCIDENT

    def can_delete(self, user):
        if self.automatique or not getattr(user, "is_authenticated", False):
            return False
        return user.is_admin_role() or self.created_by_id == user.pk


def log_status_change(dossier, ancien_statut, user, commentaire=""):
    """Record a status transition on the dossier's timeline (no-op if unchanged)."""
    if ancien_statut == dossier.statut:
        return None
    return DossierEvent.objects.create(
        dossier=dossier,
        type_evenement=TypeEvenement.CHANGEMENT_STATUT,
        ancien_statut=ancien_statut or "",
        nouveau_statut=dossier.statut,
        commentaire=commentaire,
        automatique=True,
        created_by=user,
    )
