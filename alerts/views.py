from collections import Counter

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from .services import Categorie, collect_alertes


class AlertListView(LoginRequiredMixin, TemplateView):
    template_name = "alerts/alert_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        alertes = collect_alertes(self.request.user)
        mine = bool(self.request.GET.get("mine"))
        if mine:
            alertes = [a for a in alertes if a.agent_id == self.request.user.pk]
        compteurs = Counter(a.categorie for a in alertes)
        categorie = self.request.GET.get("categorie", "")
        if categorie:
            alertes = [a for a in alertes if a.categorie == categorie]
        ctx.update({
            "alertes": alertes,
            "categories": [
                (key, label, compteurs.get(key, 0), Categorie.ICONS[key])
                for key, label in Categorie.LABELS.items()
            ],
            "total": sum(compteurs.values()),
            "current_categorie": categorie,
            "mine": mine,
        })
        return ctx
