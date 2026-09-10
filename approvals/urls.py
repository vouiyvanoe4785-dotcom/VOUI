from django.urls import path

from . import views

app_name = "approvals"

urlpatterns = [
    path(
        "demarrer/<int:content_type_id>/<int:object_id>/", views.StartValidationView.as_view(),
        name="start",
    ),
    path("etape/<int:pk>/", views.ValidationActionView.as_view(), name="action"),
]
