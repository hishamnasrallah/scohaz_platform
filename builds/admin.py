from django.contrib import admin
from django.utils.html import format_html, escape
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.http import HttpResponse, FileResponse
from django.utils import timezone
from django.shortcuts import redirect
from django.db import models
import os

from .models import Build, BuildLog
from .forms import BuildForm
from .admin_actions import retry_failed_builds, cleanup_old_builds, export_build_report
from admin_utils.admin_mixins import TimestampMixin, StatusColorMixin


class BuildLogInline(admin.TabularInline):
    model = BuildLog
    extra = 0
    can_delete = False
    readonly_fields = ['created_at', 'level', 'message_preview']
    fields = ['created_at', 'level', 'message_preview']

    def message_preview(self, obj):
        if len(obj.message) > 100:
            return f'{obj.message[:100]}...'
        return obj.message
    message_preview.short_description = 'Message'

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Build)
class BuildAdmin(TimestampMixin, StatusColorMixin, admin.ModelAdmin):
    form = BuildForm
    list_display = ['build_number', 'project_link', 'version_number', 'status_display',
                    'build_type', 'duration', 'apk_size', 'created_at', 'actions_display']
    list_filter = ['status', 'build_type', 'created_at', 'project__user']
    search_fields = ['project__name', 'version_number', 'build_number']
    readonly_fields = ['build_number', 'created_at', 'updated_at', 'started_at',
                       'completed_at', 'duration', 'build_info', 'build_output',
                       'error_details', 'download_stats']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Build Information', {
            'fields': ('project', 'build_number', 'version_number', 'build_type', 'status')
        }),
        ('Build Configuration', {
            'fields': ('generation_config',),
            'classes': ('collapse',)
        }),
        ('Build Progress', {
            'fields': ('progress', 'flutter_version', 'dart_version'),
            'classes': ('collapse',)
        }),
        ('Build Output', {
            'fields': ('apk_file', 'apk_size', 'error_message'),
            'classes': ('wide',)
        }),
        ('Build Statistics', {
            'fields': ('build_info', 'download_stats'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'started_at', 'completed_at', 'duration_seconds'),
            'classes': ('collapse',)
        })
    )

    inlines = [BuildLogInline]
    actions = [retry_failed_builds, cleanup_old_builds, export_build_report]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('project', 'project__user').prefetch_related('logs')

    def build_number(self, obj):
        return format_html(
            '<span class="build-number">#{}</span>',
            obj.build_number or obj.pk
        )
    build_number.short_description = 'Build #'
    build_number.admin_order_field = 'build_number'

    def project_link(self, obj):
        url = reverse('admin:projects_flutterproject_change', args=[obj.project.pk])
        return format_html(
            '<a href="{}">{}</a>',
            url, obj.project.name
        )
    project_link.short_description = 'Project'
    project_link.admin_order_field = 'project__name'

    def status_display(self, obj):
        status_data = self.get_status_info(obj.status)

        # Add spinner for building status
        if obj.status == 'building':
            return format_html(
                '<span class="status-badge" style="background-color: {}; color: {};">'
                '<span class="spinner"></span> {}</span>',
                status_data['bg'], status_data['color'], status_data['label']
            )

        return format_html(
            '<span class="status-badge" style="background-color: {}; color: {};">{}</span>',
            status_data['bg'], status_data['color'], status_data['label']
        )

    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'

    def duration(self, obj):
        if obj.started_at and obj.completed_at:
            duration = obj.completed_at - obj.started_at
            minutes = int(duration.total_seconds() / 60)
            seconds = int(duration.total_seconds() % 60)
            return f'{minutes}m {seconds}s'
        elif obj.started_at and obj.status == 'building':
            duration = timezone.now() - obj.started_at
            minutes = int(duration.total_seconds() / 60)
            return format_html(
                '<span class="duration-running">{} min (running...)</span>',
                minutes
            )
        return '-'
    duration.short_description = 'Duration'

    def apk_size(self, obj):
        if obj.apk_file:
            try:
                size = obj.apk_file.size
                # Convert to MB
                size_mb = size / (1024 * 1024)
                return f'{size_mb:.1f} MB'
            except:
                return '-'
        return '-'
    apk_size.short_description = 'APK Size'

    def actions_display(self, obj):
        buttons = []

        if obj.status == 'success' and obj.apk_file:
            download_url = reverse('admin:builds_build_download', args=[obj.pk])
            buttons.append(
                f'<a class="button button-small button-success" href="{download_url}">'
                f'<span class="icon">⬇</span> Download</a>'
            )

        if obj.status in ['failed', 'cancelled']:
            retry_url = reverse('admin:builds_build_retry', args=[obj.pk])
            buttons.append(
                f'<a class="button button-small button-warning" href="{retry_url}">'
                f'<span class="icon">🔄</span> Retry</a>'
            )

        if obj.status == 'building':
            cancel_url = reverse('admin:builds_build_cancel', args=[obj.pk])
            buttons.append(
                f'<a class="button button-small button-danger" href="{cancel_url}">'
                f'<span class="icon">✖</span> Cancel</a>'
            )

        logs_url = reverse('admin:builds_build_logs', args=[obj.pk])
        buttons.append(
            f'<a class="button button-small" href="{logs_url}">'
            f'<span class="icon">📋</span> Logs</a>'
        )

        return format_html(' '.join(buttons))
    actions_display.short_description = 'Actions'

    def build_info(self, obj):
        info = {
            'Build Number': obj.build_number or f'#{obj.pk}',
            'Version': obj.version,
            'Platform': obj.platform,
            'Status': obj.status.title(),
            'Flutter Version': obj.build_config.get('flutter_version', 'Unknown') if obj.build_config else 'Unknown',
            'Build Mode': obj.build_config.get('build_mode', 'release') if obj.build_config else 'release',
            'Started': obj.started_at.strftime('%Y-%m-%d %H:%M:%S') if obj.started_at else 'Not started',
            'Completed': obj.completed_at.strftime('%Y-%m-%d %H:%M:%S') if obj.completed_at else 'Not completed',
            'Duration': self.duration(obj),
            'APK Size': self.apk_size(obj),
            'Downloads': obj.download_count
        }

        html = '<table class="info-table">'
        for key, value in info.items():
            html += f'<tr><th>{key}:</th><td>{value}</td></tr>'
        html += '</table>'

        return mark_safe(html)
    build_info.short_description = 'Build Information'

    def build_output(self, obj):
        if not obj.build_log:
            return 'No build output available'

        # Format build log with syntax highlighting
        output_html = '<div class="build-output">'

        # Add command that was run
        if obj.build_config and 'command' in obj.build_config:
            output_html += f'<div class="build-command">$ {obj.build_config["command"]}</div>'

        # Add the actual output
        output_html += f'<pre class="build-log">{escape(obj.build_log[-5000:])}</pre>'  # Last 5000 chars

        if len(obj.build_log) > 5000:
            output_html += '<p class="truncated-message">Output truncated. Download full logs for complete output.</p>'

        output_html += '</div>'

        return mark_safe(output_html)
    build_output.short_description = 'Build Output'

    def error_details(self, obj):
        if obj.status != 'failed' or not obj.error_message:
            return '-'

        error_html = f'<div class="error-details">'
        error_html += f'<div class="error-message">{escape(obj.error_message)}</div>'

        if obj.error_stacktrace:
            error_html += f'<details><summary>Stack Trace</summary>'
            error_html += f'<pre class="stacktrace">{escape(obj.error_stacktrace)}</pre>'
            error_html += f'</details>'

        error_html += '</div>'

        return mark_safe(error_html)
    error_details.short_description = 'Error Details'

    def download_stats(self, obj):
        """Show download statistics"""
        stats_html = '<div class="download-stats">'
        stats_html += f'<p>Total Downloads: <strong>{obj.download_count}</strong></p>'

        if obj.download_count > 0 and hasattr(obj, 'downloadlog_set'):
            # Recent downloads
            recent_downloads = obj.downloadlog_set.order_by('-downloaded_at')[:5]
            if recent_downloads:
                stats_html += '<h4>Recent Downloads:</h4>'
                stats_html += '<ul>'
                for download in recent_downloads:
                    stats_html += f'<li>{download.user} - {download.downloaded_at.strftime("%Y-%m-%d %H:%M")}</li>'
                stats_html += '</ul>'

        stats_html += '</div>'
        return mark_safe(stats_html)
    download_stats.short_description = 'Download Statistics'

    def save_model(self, request, obj, form, change):
        if not change:  # New build
            # Set build number
            last_build = Build.objects.filter(project=obj.project).order_by('-build_number').first()
            obj.build_number = (last_build.build_number + 1) if last_build and last_build.build_number else 1

            # Set initial status
            if not obj.status:
                obj.status = 'pending'

        super().save_model(request, obj, form, change)

        # Trigger build if status is pending
        if obj.status == 'pending' and not change:
            messages.info(request, f'Build #{obj.build_number} queued for project {obj.project.name}')

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<int:build_id>/download/', self.download_view, name='builds_build_download'),
            path('<int:build_id>/retry/', self.retry_view, name='builds_build_retry'),
            path('<int:build_id>/cancel/', self.cancel_view, name='builds_build_cancel'),
            path('<int:build_id>/logs/', self.logs_view, name='builds_build_logs'),
        ]
        return custom_urls + urls

    def download_view(self, request, build_id):
        build = Build.objects.get(pk=build_id)
        if build.apk_file:
            # Update download count
            build.download_count += 1
            build.save(update_fields=['download_count'])

            # Log the download
            if hasattr(build, 'downloadlog_set'):
                build.downloadlog_set.create(user=request.user)

            # Serve the file
            response = FileResponse(
                build.apk_file.open('rb'),
                content_type='application/vnd.android.package-archive'
            )
            response['Content-Disposition'] = f'attachment; filename="{build.project.package_name}-{build.version}.apk"'
            return response

        messages.error(request, 'APK file not found')
        return redirect('admin:builds_build_change', build_id)

    def retry_view(self, request, build_id):
        build = Build.objects.get(pk=build_id)

        # Create new build with same configuration
        new_build = Build.objects.create(
            project=build.project,
            version=build.version,
            platform=build.platform,
            build_config=build.build_config,
            status='pending'
        )

        messages.success(request, f'Build #{new_build.build_number} created and queued')
        return redirect('admin:builds_build_change', new_build.pk)

    def cancel_view(self, request, build_id):
        build = Build.objects.get(pk=build_id)

        if build.status == 'building':
            build.status = 'cancelled'
            build.completed_at = timezone.now()
            build.save()

            # Add log entry
            BuildLog.objects.create(
                build=build,
                level='warning',
                message='Build cancelled by user'
            )

            messages.warning(request, f'Build #{build.build_number} cancelled')
        else:
            messages.error(request, 'Only running builds can be cancelled')

        return redirect('admin:builds_build_change', build_id)

    def logs_view(self, request, build_id):
        build = Build.objects.get(pk=build_id)

        # Create response with full logs
        response = HttpResponse(content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="build-{build.build_number}-logs.txt"'

        # Write build info
        response.write(f'Build #{build.build_number} - {build.project.name}\n')
        response.write(f'Version: {build.version}\n')
        response.write(f'Status: {build.status}\n')
        response.write(f'Started: {build.started_at}\n')
        response.write(f'Completed: {build.completed_at}\n')
        response.write('\n' + '='*80 + '\n\n')

        # Write build output
        if build.build_log:
            response.write('BUILD OUTPUT:\n')
            response.write(build.build_log)
            response.write('\n\n')

        # Write log entries
        response.write('BUILD LOGS:\n')
        for log in build.buildlog_set.order_by('timestamp'):
            response.write(f'[{log.timestamp.strftime("%Y-%m-%d %H:%M:%S")}] [{log.level.upper()}] {log.message}\n')

        return response

    class Media:
        css = {
            'all': ('admin/css/custom_admin.css', 'admin/css/build_admin.css')
        }
        js = ('admin/js/build_monitor.js',)


@admin.register(BuildLog)
class BuildLogAdmin(admin.ModelAdmin):
    list_display = ['build_link', 'created_at', 'level_display', 'message_preview']
    list_filter = ['level', 'created_at', 'build__status']
    readonly_fields = ['build', 'created_at', 'level', 'message', 'details']
    date_hierarchy = 'created_at'
    search_fields = ['message', 'build__build_number']

    def build_link(self, obj):
        url = reverse('admin:builds_build_change', args=[obj.build.pk])
        return format_html(
            '<a href="{}">Build #{}</a>',
            url, obj.build.build_number or obj.build.pk
        )
    build_link.short_description = 'Build'
    build_link.admin_order_field = 'build__build_number'

    def level_display(self, obj):
        level_colors = {
            'debug': 'gray',
            'info': 'blue',
            'warning': 'orange',
            'error': 'red',
            'critical': 'darkred'
        }
        color = level_colors.get(obj.level, 'black')

        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.level.upper()
        )
    level_display.short_description = 'Level'
    level_display.admin_order_field = 'level'

    def message_preview(self, obj):
        if len(obj.message) > 200:
            return format_html(
                '<span title="{}">{}</span>',
                escape(obj.message),
                obj.message[:200] + '...'
            )
        return obj.message
    message_preview.short_description = 'Message'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }