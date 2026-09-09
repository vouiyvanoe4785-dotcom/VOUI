from django.contrib import admin

from .models import Quote, QuoteLine, Invoice, InvoiceLine, Payment, Reminder


class QuoteLineInline(admin.TabularInline):
    model = QuoteLine
    extra = 1


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ("reference", "type_devis", "client", "dossier", "statut", "date_creation")
    list_filter = ("type_devis", "statut")
    search_fields = ("reference", "client__raison_sociale")
    inlines = [QuoteLineInline]


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 1


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("reference", "client", "dossier", "statut", "date_emission", "date_echeance")
    list_filter = ("statut",)
    search_fields = ("reference", "client__raison_sociale")
    inlines = [InvoiceLineInline, PaymentInline]


admin.site.register(Reminder)
