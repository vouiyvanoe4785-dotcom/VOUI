from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import CreateView, DeleteView

from dossiers.models import Dossier

from .forms import DocumentForm
from .models import Document


class DocumentCreateView(LoginRequiredMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = "documents/document_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.dossier = get_object_or_404(Dossier, pk=kwargs["dossier_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["dossier"] = self.dossier
        return ctx

    def form_valid(self, form):
        form.instance.dossier = self.dossier
        form.instance.uploaded_by = self.request.user
        messages.success(self.request, "Document ajouté au dossier.")
        return super().form_valid(form)

    def get_success_url(self):
        return self.dossier.get_absolute_url() + "#documents"


class DocumentDeleteView(LoginRequiredMixin, DeleteView):
    model = Document

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        dossier = self.object.dossier
        self.object.delete()
        messages.success(request, "Document supprimé.")
        return redirect(dossier.get_absolute_url() + "#documents")
