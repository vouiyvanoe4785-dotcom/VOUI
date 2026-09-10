from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View

from .forms import DossierForm
from .models import Dossier, StatutDossier, TypeOperation


class DossierListView(LoginRequiredMixin, ListView):
    model = Dossier
    template_name = "dossiers/dossier_list.html"
    context_object_name = "dossiers"
    paginate_by = 20

    def get_queryset(self):
        qs = Dossier.objects.select_related("client", "agent_responsable")
        q = self.request.GET.get("q")
        statut = self.request.GET.get("statut")
        type_operation = self.request.GET.get("type")
        if q:
            qs = qs.filter(
                Q(reference__icontains=q) | Q(reference_client__icontains=q)
                | Q(client__raison_sociale__icontains=q) | Q(donneur_ordre__icontains=q)
            )
        if statut:
            qs = qs.filter(statut=statut)
        if type_operation:
            qs = qs.filter(type_operation=type_operation)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["statuts"] = StatutDossier.choices
        ctx["types"] = TypeOperation.choices
        ctx["current_statut"] = self.request.GET.get("statut", "")
        ctx["current_type"] = self.request.GET.get("type", "")
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class DossierDetailView(LoginRequiredMixin, DetailView):
    model = Dossier
    template_name = "dossiers/dossier_detail.html"
    context_object_name = "dossier"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["marchandises"] = self.object.marchandises.all()
        ctx["documents"] = self.object.documents.all()
        ctx["devis"] = self.object.devis.all()
        ctx["factures"] = self.object.factures.all()
        ctx["achats"] = self.object.achats.all()
        return ctx


class DossierCreateView(LoginRequiredMixin, CreateView):
    model = Dossier
    form_class = DossierForm
    template_name = "dossiers/dossier_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Dossier créé avec succès.")
        return super().form_valid(form)


class DossierUpdateView(LoginRequiredMixin, UpdateView):
    model = Dossier
    form_class = DossierForm
    template_name = "dossiers/dossier_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Dossier mis à jour.")
        return super().form_valid(form)


class DossierValidateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        dossier = get_object_or_404(Dossier, pk=pk)
        if not request.user.can_validate():
            return HttpResponseForbidden("Vous n'êtes pas autorisé à valider ce dossier.")
        dossier.valide = True
        dossier.valide_par = request.user
        dossier.valide_le = timezone.now()
        dossier.save(update_fields=["valide", "valide_par", "valide_le"])
        messages.success(request, f"Dossier {dossier.reference} validé.")
        return redirect("dossiers:detail", pk=pk)
