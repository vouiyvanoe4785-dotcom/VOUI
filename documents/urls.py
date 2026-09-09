from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    path("dossier/<int:dossier_pk>/ajouter/", views.DocumentCreateView.as_view(), name="create"),
    path("<int:pk>/supprimer/", views.DocumentDeleteView.as_view(), name="delete"),
]
