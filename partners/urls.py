from django.urls import path

from . import views

app_name = "partners"

urlpatterns = [
    path("", views.PartnerListView.as_view(), name="list"),
    path("nouveau/", views.PartnerCreateView.as_view(), name="create"),
    path("<int:pk>/", views.PartnerDetailView.as_view(), name="detail"),
    path("<int:pk>/modifier/", views.PartnerUpdateView.as_view(), name="update"),
    path("<int:pk>/supprimer/", views.PartnerDeleteView.as_view(), name="delete"),
]
