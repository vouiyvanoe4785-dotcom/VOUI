from django.core.cache import cache

from .services import collect_alertes

CACHE_SECONDS = 60


def alertes(request):
    """Urgent alert count for the navbar bell, cached briefly per user."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    def compter():
        alertes = collect_alertes(user)
        return {
            "total": len(alertes),
            "urgentes": sum(1 for a in alertes if a.niveau == "danger"),
        }

    return {"alertes_compte": cache.get_or_set(f"alertes:{user.pk}", compter, CACHE_SECONDS)}
