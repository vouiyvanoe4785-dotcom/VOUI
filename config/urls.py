from django.conf import settings
from django.conf.urls.static import static
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
    path("", include("billing.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
