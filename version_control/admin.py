from django.contrib import admin
from .models import Repository, Branch, Commit, FileVersion

class RepositoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'scope', 'owner', 'created_at', 'is_deleted')
    list_filter = ('scope', 'is_deleted')

admin.site.register(Repository, RepositoryAdmin)
admin.site.register(Branch)
admin.site.register(Commit)
admin.site.register(FileVersion)
