from django.urls import path

from . import views

app_name = "tracking"

urlpatterns = [
    path("", views.ActivityListView.as_view(), name="activity"),
    path("dossier/<int:dossier_pk>/ajouter/", views.EventCreateView.as_view(), name="create"),
    path("<int:pk>/supprimer/", views.EventDeleteView.as_view(), name="delete"),
]
