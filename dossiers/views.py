from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from accounts.models import Role
from approvals.workflows import get_steps
from tracking.models import log_status_change

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
        ctx["evenements"] = self.object.evenements.select_related("created_by")
        ctx["can_add_event"] = self.request.user.role != Role.CONSULTATION
        ctx["validation_steps"] = get_steps(self.object)
        ctx["validation_ct_id"] = ContentType.objects.get_for_model(Dossier).id
        ctx["validation_object_id"] = self.object.pk
        return ctx


class DossierCreateView(LoginRequiredMixin, CreateView):
    model = Dossier
    form_class = DossierForm
    template_name = "dossiers/dossier_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        log_status_change(self.object, "", self.request.user, commentaire="Ouverture du dossier")
        messages.success(self.request, "Dossier créé avec succès.")
        return response


class DossierUpdateView(LoginRequiredMixin, UpdateView):
    model = Dossier
    form_class = DossierForm
    template_name = "dossiers/dossier_form.html"

    def form_valid(self, form):
        ancien_statut = Dossier.objects.values_list("statut", flat=True).get(pk=self.object.pk)
        response = super().form_valid(form)
        log_status_change(self.object, ancien_statut, self.request.user)
        messages.success(self.request, "Dossier mis à jour.")
        return response
