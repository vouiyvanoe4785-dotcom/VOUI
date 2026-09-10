from django.contrib import admin

from .models import SupplierInvoice, SupplierInvoiceLine, SupplierPayment


class SupplierInvoiceLineInline(admin.TabularInline):
    model = SupplierInvoiceLine
    extra = 1


class SupplierPaymentInline(admin.TabularInline):
    model = SupplierPayment
    extra = 0


@admin.register(SupplierInvoice)
class SupplierInvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "reference", "fournisseur", "dossier", "statut", "date_facture", "date_echeance",
    )
    list_filter = ("statut",)
    search_fields = ("reference", "reference_fournisseur", "fournisseur__raison_sociale")
    inlines = [SupplierInvoiceLineInline, SupplierPaymentInline]
