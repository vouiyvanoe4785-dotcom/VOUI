from django.contrib import admin

from .models import Dossier


@admin.register(Dossier)
class DossierAdmin(admin.ModelAdmin):
    list_display = (
        "reference", "client", "type_operation", "statut", "agent_responsable", "date_ouverture",
    )
    list_filter = ("type_operation", "statut", "regime_douanier", "incoterm")
    search_fields = ("reference", "reference_client", "client__raison_sociale", "donneur_ordre")
    date_hierarchy = "date_ouverture"
