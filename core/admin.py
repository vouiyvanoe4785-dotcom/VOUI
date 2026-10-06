from django.contrib import admin

from .models import Societe


@admin.register(Societe)
class SocieteAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not Societe.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
