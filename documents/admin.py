from django.contrib import admin

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("libelle", "dossier", "type_document", "date_document", "uploaded_at")
    list_filter = ("type_document",)
    search_fields = ("libelle", "dossier__reference")
