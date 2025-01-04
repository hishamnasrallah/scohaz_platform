from django.contrib import admin
# Register your models here.
from version.forms import VersionAdminForm
from version.models import Version, LocalVersion


@admin.register(LocalVersion)
class LocalVersionAdmin(admin.ModelAdmin):
    list_display = ('lang', 'version_number', 'active_ind')
    list_filter = ('lang', 'active_ind')
    search_fields = ('version_number',)
    ordering = ('lang', 'version_number')


@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    form = VersionAdminForm
    list_display = ('version_number', 'active_ind',
                    'operating_system', 'expiration_date')
