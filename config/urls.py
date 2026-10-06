from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("dashboard.urls")),
    path("comptes/", include("accounts.urls")),
    path("partenaires/", include("partners.urls")),
    path("dossiers/", include("dossiers.urls")),
    path("cargo/", include("cargo.urls")),
    path("documents/", include("documents.urls")),
    path("caisse/", include("treasury.urls")),
    path("achats/", include("purchasing.urls")),
    path("validations/", include("approvals.urls")),
    path("rapports/", include("reports.urls")),
    path("suivi/", include("tracking.urls")),
    path("parametres/", include("core.urls")),
    path("alertes/", include("alerts.urls")),
    path("portail/", include("portal.urls")),
    path("", include("billing.urls")),
]

# Uploaded files are deliberately not served from MEDIA_URL, not even in development:
# they go through views that check access (documents:download, portal:document_download).
