from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from .forms import SocieteForm
from .models import Societe


class SocieteUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    form_class = SocieteForm
    template_name = "core/societe_form.html"
    success_url = reverse_lazy("core:societe")

    def test_func(self):
        return self.request.user.is_admin_role()

    def get_object(self, queryset=None):
        return Societe.load()

    def form_valid(self, form):
        messages.success(self.request, "Informations de la société mises à jour.")
        return super().form_valid(form)
