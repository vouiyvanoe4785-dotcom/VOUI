from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.AydenLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("equipe/", views.TeamListView.as_view(), name="team_list"),
    path("equipe/nouveau/", views.TeamCreateView.as_view(), name="team_create"),
]
