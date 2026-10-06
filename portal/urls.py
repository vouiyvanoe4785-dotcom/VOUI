from django.urls import path

from . import views

app_name = "portal"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("dossiers/", views.DossierListView.as_view(), name="dossier_list"),
    path("dossiers/<int:pk>/", views.DossierDetailView.as_view(), name="dossier_detail"),
    path("documents/<int:pk>/", views.DocumentDownloadView.as_view(), name="document_download"),
    path("factures/", views.InvoiceListView.as_view(), name="invoice_list"),
    path("factures/<int:pk>/pdf/", views.InvoicePdfView.as_view(), name="invoice_pdf"),
    path("devis/", views.QuoteListView.as_view(), name="quote_list"),
    path("devis/<int:pk>/pdf/", views.QuotePdfView.as_view(), name="quote_pdf"),
]
