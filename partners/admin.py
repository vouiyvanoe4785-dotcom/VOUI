from django.contrib import admin

from .models import Partner


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("raison_sociale", "type_tiers", "telephone", "email", "ville", "is_active")
    list_filter = ("type_tiers", "is_active", "pays")
    search_fields = ("raison_sociale", "ice", "rc", "email", "telephone")
