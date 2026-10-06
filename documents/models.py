from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models

from dossiers.models import Dossier

ALLOWED_DOCUMENT_EXTENSIONS = [
    "pdf", "jpg", "jpeg", "png", "tif", "tiff",
    "doc", "docx", "xls", "xlsx", "csv", "txt",
]


class TypeDocument(models.TextChoices):
    FACTURE_COMMERCIALE = "facture_commerciale", "Facture commerciale"
    CONNAISSEMENT = "connaissement", "Connaissement (B/L)"
    LTA = "lta", "Lettre de transport aérien (LTA)"
    CMR = "cmr", "Lettre de voiture (CMR)"
    PACKING_LIST = "packing_list", "Liste de colisage"
    CERTIFICAT_ORIGINE = "certificat_origine", "Certificat d'origine"
    DAU = "dau", "Déclaration en douane (DUM/DAU)"
    ASSURANCE = "assurance", "Attestation d'assurance"
    AUTORISATION = "autorisation", "Autorisation / licence"
    AUTRE = "autre", "Autre"


def document_upload_path(instance, filename):
    return f"dossiers/{instance.dossier.reference}/documents/{filename}"


class Document(models.Model):
    dossier = models.ForeignKey(
        Dossier, verbose_name="Dossier", on_delete=models.CASCADE, related_name="documents"
    )
    type_document = models.CharField(
        "Type de document", max_length=30, choices=TypeDocument.choices
    )
    libelle = models.CharField("Libellé", max_length=200, blank=True)
    fichier = models.FileField(
        "Fichier", upload_to=document_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=ALLOWED_DOCUMENT_EXTENSIONS)],
    )
    date_document = models.DateField("Date du document", null=True, blank=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Document"
        verbose_name_plural = "Documents"

    def __str__(self):
        return self.libelle or self.get_type_document_display()

    def filename(self):
        return self.fichier.name.rsplit("/", 1)[-1]
