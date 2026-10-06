from django.contrib import admin

from .models import DossierEvent


@admin.register(DossierEvent)
class DossierEventAdmin(admin.ModelAdmin):
    list_display = ("dossier", "type_evenement", "date_evenement", "lieu", "automatique", "created_by")
    list_filter = ("type_evenement", "automatique")
    search_fields = ("dossier__reference", "commentaire", "lieu")
    date_hierarchy = "date_evenement"
