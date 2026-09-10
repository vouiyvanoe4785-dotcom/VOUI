from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.ServiceReportView.as_view(), name="service_report"),
    path("export.csv", views.ServiceReportExportView.as_view(), name="service_report_export"),
]
