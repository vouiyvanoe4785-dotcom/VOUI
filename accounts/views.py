from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from .forms import UserCreateForm
from .models import User


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
        return User.objects.all().order_by("username")


class TeamCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = User
    form_class = UserCreateForm
    template_name = "accounts/team_form.html"
    success_url = reverse_lazy("accounts:team_list")

    def test_func(self):
        return self.request.user.is_admin_role()

    def form_valid(self, form):
        messages.success(self.request, "Utilisateur créé avec succès.")
        return super().form_valid(form)
