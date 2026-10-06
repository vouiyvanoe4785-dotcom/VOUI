from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView

from core.models import Societe

from .forms import UserCreateForm
from .models import User
from .passwords import (
    EMAIL_TEMPLATE, SUBJECT_TEMPLATE, envoyer_lien_reinitialisation, extra_email_context,
)


class AydenLoginView(LoginView):
    template_name = "accounts/login.html"


class TeamListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = User
    template_name = "accounts/team_list.html"
    context_object_name = "users"
    paginate_by = 25

    def test_func(self):
        return self.request.user.is_admin_role()

    def get_queryset(self):
        return User.objects.select_related("partner").order_by("username")


class TeamCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = User
    form_class = UserCreateForm
    template_name = "accounts/team_form.html"
    success_url = reverse_lazy("accounts:team_list")

    def test_func(self):
        return self.request.user.is_admin_role()

    def get_initial(self):
        initial = super().get_initial()
        for key in ("role", "partner"):
            if self.request.GET.get(key):
                initial[key] = self.request.GET[key]
        return initial

    def get_success_url(self):
        if self.object.partner_id:
            return reverse("partners:detail", args=[self.object.partner_id])
        return super().get_success_url()

    def form_valid(self, form):
        messages.success(self.request, "Utilisateur créé avec succès.")
        return super().form_valid(form)


# --- Mots de passe -------------------------------------------------------------------

class PasswordResetView(auth_views.PasswordResetView):
    """Ask for a reset link by e-mail. Same answer whether or not the address exists."""

    template_name = "accounts/password_reset_form.html"
    email_template_name = EMAIL_TEMPLATE
    subject_template_name = SUBJECT_TEMPLATE
    success_url = reverse_lazy("accounts:password_reset_done")

    def form_valid(self, form):
        self.extra_email_context = extra_email_context()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["validite_heures"] = extra_email_context()["validite_heures"]
        return ctx


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


class PasswordChangeView(auth_views.PasswordChangeView):
    """Change one's own password, from the staff app or the client portal."""

    template_name = "accounts/password_change_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_client_portal:
            ctx.update({"base_template": "portal/base.html", "partner": user.partner, "societe": Societe.load()})
        else:
            ctx["base_template"] = "base.html"
        return ctx

    def get_success_url(self):
        messages.success(self.request, "Votre mot de passe a été modifié.")
        return reverse("portal:home") if self.request.user.is_client_portal else reverse("dashboard:home")


class SendResetLinkView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Admins send a reset link to a user instead of choosing (and knowing) their password."""

    def test_func(self):
        return self.request.user.is_admin_role()

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk, is_active=True)
        if not user.email:
            messages.error(request, f"{user} n'a pas d'adresse e-mail : ajoutez-la avant d'envoyer un lien.")
        else:
            envoyer_lien_reinitialisation(request, user)
            messages.success(request, f"Lien de réinitialisation envoyé à {user.email}.")
        return redirect(request.POST.get("next") or "accounts:team_list")
