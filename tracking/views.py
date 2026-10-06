from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import CreateView, ListView

from accounts.models import Role
from dossiers.models import Dossier

from .forms import DossierEventForm
from .models import DossierEvent, TypeEvenement, log_status_change


class EventCreateView(LoginRequiredMixin, CreateView):
    model = DossierEvent
    form_class = DossierEventForm
    template_name = "tracking/event_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.dossier = get_object_or_404(Dossier, pk=kwargs["dossier_pk"])
        if request.user.is_authenticated and request.user.role == Role.CONSULTATION:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["dossier"] = self.dossier
        return ctx

    @transaction.atomic
    def form_valid(self, form):
        form.instance.dossier = self.dossier
        form.instance.created_by = self.request.user
        response = super().form_valid(form)

        nouveau_statut = form.cleaned_data.get("changer_statut")
        if nouveau_statut and nouveau_statut != self.dossier.statut:
            ancien = self.dossier.statut
            self.dossier.statut = nouveau_statut
            self.dossier.save(update_fields=["statut", "updated_at"])
            log_status_change(
                self.dossier, ancien, self.request.user,
                commentaire=f"Suite à : {self.object.get_type_evenement_display()}",
            )
        messages.success(self.request, "Événement ajouté au suivi du dossier.")
        return response

    def get_success_url(self):
        return self.dossier.get_absolute_url() + "#suivi"


class EventDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        event = get_object_or_404(DossierEvent, pk=pk)
        if not event.can_delete(request.user):
            raise PermissionDenied
        dossier = event.dossier
        event.delete()
        messages.success(request, "Événement supprimé.")
        return redirect(dossier.get_absolute_url() + "#suivi")


class ActivityListView(LoginRequiredMixin, ListView):
    """Cross-dossier activity feed: everything that happened, newest first."""

    model = DossierEvent
    template_name = "tracking/activity_list.html"
    context_object_name = "evenements"
    paginate_by = 30

    def get_queryset(self):
        qs = DossierEvent.objects.select_related("dossier", "dossier__client", "created_by")
        type_evenement = self.request.GET.get("type")
        if type_evenement:
            qs = qs.filter(type_evenement=type_evenement)
        if self.request.GET.get("mine"):
            qs = qs.filter(dossier__agent_responsable=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["types"] = TypeEvenement.choices
        ctx["current_type"] = self.request.GET.get("type", "")
        ctx["mine"] = bool(self.request.GET.get("mine"))
        return ctx
