from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("societe/", views.SocieteUpdateView.as_view(), name="societe"),
    path("logo/", views.logo, name="logo"),
]
