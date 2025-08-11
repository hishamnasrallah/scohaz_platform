from django.contrib import admin
from django.utils.html import format_html
from .models import Build, BuildLog


@admin.register(Build)
class BuildAdmin(admin.ModelAdmin):
    list_display = ['id', 'project', 'status_badge', 'build_type', 'version_number',
                    'build_number', 'apk_size_display', 'duration_display', 'created_at',
                    'download_button']
    list_filter = ['status', 'build_type', 'created_at', 'project__user']
    search_fields = ['project__name', 'project__package_name', 'version_number']
    readonly_fields = ['project', 'status', 'apk_file', 'apk_size', 'flutter_version',
                       'dart_version', 'error_message', 'created_at', 'started_at',
                       'completed_at', 'duration_seconds']

    fieldsets = (
        ('Project Information', {
            'fields': ('project',)
        }),
        ('Build Configuration', {
            'fields': ('build_type', 'version_number', 'build_number')
        }),
        ('Build Status', {
            'fields': ('status', 'error_message')
        }),
        ('Build Output', {
            'fields': ('apk_file', 'apk_size')
        }),
        ('Build Environment', {
            'fields': ('flutter_version', 'dart_version')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'started_at', 'completed_at', 'duration_seconds')
        }),
    )

    def download_button(self, obj):
        if obj.status == 'success' and obj.apk_file:
            return format_html(
                '<a class="button" href="{}" download>Download APK</a>',
                obj.apk_file.url
            )
        return '-'

    download_button.short_description = 'Download'

    def status_badge(self, obj):
        colors = {
            'pending': '#FFA500',
            'building': '#007BFF',
            'success': '#28A745',
            'failed': '#DC3545',
            'cancelled': '#6C757D',
        }
        color = colors.get(obj.status, '#6C757D')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )

    status_badge.short_description = 'Status'

    def apk_size_display(self, obj):
        if obj.apk_size:
            size_mb = obj.apk_size / (1024 * 1024)
            return f"{size_mb:.2f} MB"
        return "-"

    apk_size_display.short_description = 'APK Size'

    def duration_display(self, obj):
        if obj.duration_seconds:
            minutes, seconds = divmod(obj.duration_seconds, 60)
            if minutes > 0:
                return f"{minutes}m {seconds}s"
            return f"{seconds}s"
        return "-"

    duration_display.short_description = 'Duration'

    def has_add_permission(self, request):
        return False


@admin.register(BuildLog)
class BuildLogAdmin(admin.ModelAdmin):
    list_display = ['build', 'timestamp', 'level_badge', 'stage', 'message_preview']
    list_filter = ['level', 'stage', 'timestamp']
    search_fields = ['message', 'build__project__name']
    readonly_fields = ['build', 'timestamp', 'level', 'stage', 'message']

    def level_badge(self, obj):
        colors = {
            'info': '#17A2B8',
            'warning': '#FFC107',
            'error': '#DC3545',
        }
        color = colors.get(obj.level, '#6C757D')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 3px;">{}</span>',
            color, obj.level.upper()
        )

    level_badge.short_description = 'Level'

    def message_preview(self, obj):
        if len(obj.message) > 100:
            return obj.message[:100] + "..."
        return obj.message

    message_preview.short_description = 'Message'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False