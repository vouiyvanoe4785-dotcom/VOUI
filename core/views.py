from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.decorators.http import require_GET
from django.views.generic import UpdateView

from .files import serve_file
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


@require_GET
def logo(request):
    """The company logo is the one uploaded file that is public (portal header, login)."""
    societe = Societe.load()
    response = serve_file(societe.logo, societe.logo.name.rsplit("/", 1)[-1] if societe.logo else "logo")
    response["Cache-Control"] = "public, max-age=3600"
    return response
