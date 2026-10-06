from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum
from django.utils import timezone
from django.views.generic import TemplateView

from billing.models import Invoice, StatutFacture
from dossiers.models import Dossier, StatutDossier, TypeOperation
from partners.models import Partner
from purchasing.models import StatutAchat, SupplierInvoice
from alerts.services import collect_alertes
from tracking.models import DossierEvent
from treasury.models import CashAccount


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        dossiers_qs = Dossier.objects.all()
        ctx["nb_dossiers_total"] = dossiers_qs.count()
        ctx["nb_dossiers_ouverts"] = dossiers_qs.exclude(
            statut__in=[StatutDossier.CLOTURE, StatutDossier.ANNULE]
        ).count()
        ctx["nb_dossiers_en_douane"] = dossiers_qs.filter(statut=StatutDossier.EN_DOUANE).count()
        ctx["nb_clients"] = Partner.objects.filter(is_active=True).count()

        ctx["dossiers_par_statut"] = (
            dossiers_qs.values("statut").annotate(total=Count("id")).order_by("statut")
        )
        ctx["statut_labels"] = dict(StatutDossier.choices)

        ctx["dossiers_par_type"] = (
            dossiers_qs.values("type_operation").annotate(total=Count("id")).order_by("type_operation")
        )
        ctx["type_labels"] = dict(TypeOperation.choices)

        invoices = Invoice.objects.exclude(statut=StatutFacture.ANNULEE)
        total_facture = sum((f.montant_total for f in invoices), 0)
        total_paye = sum((f.montant_paye for f in invoices), 0)
        ctx["total_facture"] = total_facture
        ctx["total_paye"] = total_paye
        ctx["total_impaye"] = total_facture - total_paye

        ctx["factures_impayees"] = [f for f in invoices if f.solde > 0][:10]
        ctx["dossiers_recents"] = dossiers_qs.select_related("client").order_by("-created_at")[:8]

        comptes = CashAccount.objects.filter(is_active=True)
        ctx["solde_tresorerie"] = sum((c.solde for c in comptes), 0)

        achats = SupplierInvoice.objects.exclude(statut=StatutAchat.ANNULEE)
        ctx["total_dettes_fournisseurs"] = sum(
            (a.solde for a in achats if a.solde > 0), 0
        )

        alertes = collect_alertes(self.request.user)
        ctx["alertes"] = alertes[:6]
        ctx["nb_alertes"] = len(alertes)

        ctx["activite_recente"] = DossierEvent.objects.select_related(
            "dossier", "dossier__client", "created_by"
        )[:6]

        return ctx
