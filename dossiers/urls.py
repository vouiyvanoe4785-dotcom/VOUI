from django.urls import path

from . import views

app_name = "dossiers"

urlpatterns = [
    path("", views.DossierListView.as_view(), name="list"),
    path("nouveau/", views.DossierCreateView.as_view(), name="create"),
    path("<int:pk>/", views.DossierDetailView.as_view(), name="detail"),
    path("<int:pk>/modifier/", views.DossierUpdateView.as_view(), name="update"),
    path("<int:pk>/valider/", views.DossierValidateView.as_view(), name="validate"),
]
