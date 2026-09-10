from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from accounts.models import Role


class EtapeStatut(models.TextChoices):
    EN_ATTENTE = "en_attente", "En attente"
    APPROUVEE = "approuvee", "Approuvée"
    REFUSEE = "refusee", "Refusée"


class ValidationStep(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    ordre = models.PositiveSmallIntegerField("Ordre")
    libelle = models.CharField("Étape", max_length=150)
    role_requis = models.CharField("Rôle requis", max_length=20, choices=Role.choices)

    statut = models.CharField(
        "Statut", max_length=15, choices=EtapeStatut.choices, default=EtapeStatut.EN_ATTENTE
    )
    commentaire = models.TextField("Commentaire", blank=True)

    validateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="etapes_validees",
    )
    signature_nom = models.CharField("Nom du signataire", max_length=150, blank=True)
    date_validation = models.DateTimeField("Date de validation", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["content_type", "object_id", "ordre"]
        verbose_name = "Étape de validation"
        verbose_name_plural = "Étapes de validation"

    def __str__(self):
        return f"{self.libelle} ({self.get_statut_display()})"

    @property
    def is_bloquee(self):
        return ValidationStep.objects.filter(
            content_type=self.content_type, object_id=self.object_id, ordre__lt=self.ordre,
        ).exclude(statut=EtapeStatut.APPROUVEE).exists()
