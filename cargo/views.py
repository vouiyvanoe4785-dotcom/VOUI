from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import CreateView, DeleteView, UpdateView

from dossiers.models import Dossier

from .forms import MarchandiseForm
from .models import Marchandise


class MarchandiseCreateView(LoginRequiredMixin, CreateView):
    model = Marchandise
    form_class = MarchandiseForm
    template_name = "cargo/marchandise_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.dossier = get_object_or_404(Dossier, pk=kwargs["dossier_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["dossier"] = self.dossier
        return ctx

    def form_valid(self, form):
        form.instance.dossier = self.dossier
        messages.success(self.request, "Marchandise ajoutée au dossier.")
        return super().form_valid(form)

    def get_success_url(self):
        return self.dossier.get_absolute_url() + "#marchandises"


class MarchandiseUpdateView(LoginRequiredMixin, UpdateView):
    model = Marchandise
    form_class = MarchandiseForm
    template_name = "cargo/marchandise_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["dossier"] = self.object.dossier
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Marchandise mise à jour.")
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.dossier.get_absolute_url() + "#marchandises"


class MarchandiseDeleteView(LoginRequiredMixin, DeleteView):
    model = Marchandise

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        dossier = self.object.dossier
        self.object.delete()
        messages.success(request, "Marchandise supprimée.")
        return redirect(dossier.get_absolute_url() + "#marchandises")
