from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    path("devis/", views.QuoteListView.as_view(), name="quote_list"),
    path("devis/nouveau/", views.QuoteEditView.as_view(), name="quote_create"),
    path("devis/<int:pk>/", views.QuoteDetailView.as_view(), name="quote_detail"),
    path("devis/<int:pk>/pdf/", views.QuotePdfView.as_view(), name="quote_pdf"),
    path("devis/<int:pk>/modifier/", views.QuoteEditView.as_view(), name="quote_update"),
    path("devis/<int:pk>/supprimer/", views.QuoteDeleteView.as_view(), name="quote_delete"),

    path("factures/", views.InvoiceListView.as_view(), name="invoice_list"),
    path("factures/nouvelle/", views.InvoiceEditView.as_view(), name="invoice_create"),
    path("factures/<int:pk>/", views.InvoiceDetailView.as_view(), name="invoice_detail"),
    path("factures/<int:pk>/pdf/", views.InvoicePdfView.as_view(), name="invoice_pdf"),
    path("factures/<int:pk>/modifier/", views.InvoiceEditView.as_view(), name="invoice_update"),
    path("factures/<int:pk>/supprimer/", views.InvoiceDeleteView.as_view(), name="invoice_delete"),
    path("factures/<int:invoice_pk>/paiement/", views.PaymentCreateView.as_view(), name="payment_create"),
    path("factures/<int:invoice_pk>/relance/", views.ReminderCreateView.as_view(), name="reminder_create"),
]
