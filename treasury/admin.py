from django.contrib import admin

from .models import CashAccount, CashTransaction


@admin.register(CashAccount)
class CashAccountAdmin(admin.ModelAdmin):
    list_display = ("nom", "type_compte", "devise", "solde_initial", "solde", "is_active")
    list_filter = ("type_compte", "is_active")
    search_fields = ("nom", "numero_compte")


@admin.register(CashTransaction)
class CashTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "compte", "type_mouvement", "categorie", "montant", "date_mouvement", "dossier",
    )
    list_filter = ("type_mouvement", "categorie", "compte")
    search_fields = ("description", "compte__nom", "dossier__reference")
    date_hierarchy = "date_mouvement"
