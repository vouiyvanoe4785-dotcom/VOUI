from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse

PORTAL_PREFIX = "/portail/"


class PortalAccessMiddleware:
    """Keep client accounts inside the client portal, and staff outside of it.

    Every staff view only requires a login, so client accounts must be fenced off here,
    in one place, rather than view by view.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.client_allowed = (
            PORTAL_PREFIX,
            "/comptes/logout/",
            "/comptes/mot-de-passe/",
            reverse("core:logo"),
            "/" + settings.STATIC_URL.lstrip("/"),
        )

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            in_portal = request.path.startswith(PORTAL_PREFIX)
            if user.is_client_portal:
                if not request.path.startswith(self.client_allowed):
                    return redirect("portal:home")
            elif in_portal:
                return redirect("dashboard:home")
        return self.get_response(request)
