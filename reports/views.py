import csv
import datetime
from decimal import ROUND_HALF_UP, Decimal

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse
from django.views.generic import TemplateView, View

from .services import build_report, get_available_services


class ServiceReportAccessMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.can_manage_billing()


def _parse_period(request):
    today = datetime.date.today()
    default_debut = today.replace(day=1)
    date_debut_str = request.GET.get("date_debut")
    date_fin_str = request.GET.get("date_fin")
    try:
        date_debut = datetime.date.fromisoformat(date_debut_str) if date_debut_str else default_debut
    except ValueError:
        date_debut = default_debut
    try:
        date_fin = datetime.date.fromisoformat(date_fin_str) if date_fin_str else today
    except ValueError:
        date_fin = today
    return date_debut, date_fin


class ServiceReportView(LoginRequiredMixin, ServiceReportAccessMixin, TemplateView):
    template_name = "reports/report.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        date_debut, date_fin = _parse_period(self.request)
        service = self.request.GET.get("service", "")

        rows, totaux = build_report(date_debut, date_fin, service or None)

        ctx["rows"] = rows
        ctx["totaux"] = totaux
        ctx["date_debut"] = date_debut
        ctx["date_fin"] = date_fin
        ctx["service"] = service
        ctx["services"] = get_available_services()
        return ctx


def _money(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class ServiceReportExportView(LoginRequiredMixin, ServiceReportAccessMixin, View):
    def get(self, request):
        date_debut, date_fin = _parse_period(request)
        service = request.GET.get("service", "")
        rows, totaux = build_report(date_debut, date_fin, service or None)

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="rapport_{date_debut}_{date_fin}.csv"'
        )
        writer = csv.writer(response)
        writer.writerow([
            "Service", "Dossiers ouverts", "CA facturé (MAD)", "CA encaissé (MAD)",
            "Dépenses engagées (MAD)", "Dépenses payées (MAD)", "Résultat (MAD)",
        ])
        for row in rows:
            writer.writerow([
                row["service"], row["nb_dossiers"], _money(row["ca_facture"]),
                _money(row["ca_encaisse"]), _money(row["depenses_engagees"]),
                _money(row["depenses_payees"]), _money(row["resultat"]),
            ])
        writer.writerow([
            "TOTAL", totaux["nb_dossiers"], _money(totaux["ca_facture"]),
            _money(totaux["ca_encaisse"]), _money(totaux["depenses_engagees"]),
            _money(totaux["depenses_payees"]), _money(totaux["resultat"]),
        ])
        return response
