from django.contrib import admin

from .models import ValidationStep


@admin.register(ValidationStep)
class ValidationStepAdmin(admin.ModelAdmin):
    list_display = (
        "content_type", "object_id", "ordre", "libelle", "role_requis", "statut",
        "validateur", "date_validation",
    )
    list_filter = ("content_type", "statut", "role_requis")
