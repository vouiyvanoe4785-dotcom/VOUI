from django.urls import path

from . import views

app_name = "treasury"

urlpatterns = [
    path("", views.CashAccountListView.as_view(), name="account_list"),
    path("nouveau/", views.CashAccountCreateView.as_view(), name="account_create"),
    path("virement/", views.TransferCreateView.as_view(), name="transfer_create"),
    path("<int:pk>/", views.CashAccountDetailView.as_view(), name="account_detail"),
    path("<int:pk>/modifier/", views.CashAccountUpdateView.as_view(), name="account_update"),
    path(
        "<int:account_pk>/mouvement/", views.CashTransactionCreateView.as_view(),
        name="transaction_create",
    ),
]
