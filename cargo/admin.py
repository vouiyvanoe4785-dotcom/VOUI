from django.contrib import admin

from .models import Marchandise


@admin.register(Marchandise)
class MarchandiseAdmin(admin.ModelAdmin):
    list_display = ("designation", "dossier", "code_hs", "quantite", "unite", "origine")
    list_filter = ("origine",)
    search_fields = ("designation", "code_hs", "dossier__reference")
