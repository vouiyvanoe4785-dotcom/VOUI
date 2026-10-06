from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import PartnerForm
from .models import Partner, PartnerType


class PartnerListView(LoginRequiredMixin, ListView):
    model = Partner
    template_name = "partners/partner_list.html"
    context_object_name = "partners"
    paginate_by = 20

    def get_queryset(self):
        qs = Partner.objects.all()
        q = self.request.GET.get("q")
        type_tiers = self.request.GET.get("type")
        if q:
            qs = qs.filter(
                Q(raison_sociale__icontains=q) | Q(ice__icontains=q) | Q(email__icontains=q)
                | Q(telephone__icontains=q)
            )
        if type_tiers:
            qs = qs.filter(type_tiers=type_tiers)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["types"] = PartnerType.choices
        ctx["current_type"] = self.request.GET.get("type", "")
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class PartnerDetailView(LoginRequiredMixin, DetailView):
    model = Partner
    template_name = "partners/partner_detail.html"
    context_object_name = "partner"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["dossiers"] = self.object.dossiers.all()[:10]
        ctx["achats"] = self.object.achats.all()[:10]
        ctx["comptes_portail"] = self.object.comptes_portail.order_by("username")
        return ctx


class PartnerCreateView(LoginRequiredMixin, CreateView):
    model = Partner
    form_class = PartnerForm
    template_name = "partners/partner_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Client / tiers créé avec succès.")
        return super().form_valid(form)


class PartnerUpdateView(LoginRequiredMixin, UpdateView):
    model = Partner
    form_class = PartnerForm
    template_name = "partners/partner_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Client / tiers mis à jour.")
        return super().form_valid(form)


class PartnerDeleteView(LoginRequiredMixin, DeleteView):
    model = Partner
    template_name = "partners/partner_confirm_delete.html"
    success_url = reverse_lazy("partners:list")

    def form_valid(self, form):
        messages.success(self.request, "Client / tiers supprimé.")
        return super().form_valid(form)
