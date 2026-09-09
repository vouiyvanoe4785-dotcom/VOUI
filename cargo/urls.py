from django.urls import path

from . import views

app_name = "cargo"

urlpatterns = [
    path("dossier/<int:dossier_pk>/ajouter/", views.MarchandiseCreateView.as_view(), name="create"),
    path("<int:pk>/modifier/", views.MarchandiseUpdateView.as_view(), name="update"),
    path("<int:pk>/supprimer/", views.MarchandiseDeleteView.as_view(), name="delete"),
]
