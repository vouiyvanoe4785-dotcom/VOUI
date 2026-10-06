from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.AydenLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("equipe/", views.TeamListView.as_view(), name="team_list"),
    path("equipe/nouveau/", views.TeamCreateView.as_view(), name="team_create"),
    path("equipe/<int:pk>/lien-mot-de-passe/", views.SendResetLinkView.as_view(), name="send_reset_link"),
    path("mot-de-passe/changer/", views.PasswordChangeView.as_view(), name="password_change"),
    path("mot-de-passe/oublie/", views.PasswordResetView.as_view(), name="password_reset"),
    path("mot-de-passe/oublie/envoye/", views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path(
        "mot-de-passe/reinitialiser/<uidb64>/<token>/",
        views.PasswordResetConfirmView.as_view(), name="password_reset_confirm",
    ),
    path("mot-de-passe/reinitialise/", views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
]
