from django.urls import path

from . import views

app_name = "purchasing"

urlpatterns = [
    path("", views.SupplierInvoiceListView.as_view(), name="invoice_list"),
    path("nouveau/", views.SupplierInvoiceEditView.as_view(), name="invoice_create"),
    path("<int:pk>/", views.SupplierInvoiceDetailView.as_view(), name="invoice_detail"),
    path("<int:pk>/modifier/", views.SupplierInvoiceEditView.as_view(), name="invoice_update"),
    path("<int:pk>/supprimer/", views.SupplierInvoiceDeleteView.as_view(), name="invoice_delete"),
    path(
        "<int:invoice_pk>/paiement/", views.SupplierPaymentCreateView.as_view(),
        name="payment_create",
    ),
]
