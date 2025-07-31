from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Count, Avg, Sum, Q, F
import csv
import json
from datetime import timedelta

from .models import Build, BuildLog


def retry_failed_builds(modeladmin, request, queryset):
    """Retry all failed builds in selection"""
    # Filter only failed builds
    failed_builds = queryset.filter(status='failed')

    if not failed_builds.exists():
        messages.warning(request, 'No failed builds selected.')
        return

    retry_count = 0

    for build in failed_builds:
        # Create new build with same configuration
        new_build = Build.objects.create(
            project=build.project,
            version=build.version,
            platform=build.platform,
            build_config=build.build_config,
            environment_variables=build.environment_variables,
            commit_hash=build.commit_hash,
            status='pending'
        )

        # Log the retry
        BuildLog.objects.create(
            build=new_build,
            level='info',
            message=f'Retry of failed build #{build.build_number or build.pk}'
        )

        retry_count += 1

    messages.success(
        request,
        f'Created {retry_count} new build(s) to retry failed builds.'
    )

retry_failed_builds.short_description = 'Retry failed builds'


def cleanup_old_builds(modeladmin, request, queryset):
    """Clean up old builds and their files"""
    if 'confirm' in request.POST:
        days = int(request.POST.get('days', 30))
        keep_success = request.POST.get('keep_success') == 'on'

        cutoff_date = timezone.now() - timedelta(days=days)

        # Filter builds to delete
        builds_to_delete = queryset.filter(created_at__lt=cutoff_date)

        if keep_success:
            builds_to_delete = builds_to_delete.exclude(status='success')

        # Count APK files that will be deleted
        apk_count = builds_to_delete.exclude(apk_file='').count()

        # Delete APK files
        for build in builds_to_delete:
            if build.apk_file:
                try:
                    build.apk_file.delete(save=False)
                except:
                    pass  # File might not exist

        # Delete builds
        deleted_count = builds_to_delete.count()
        builds_to_delete.delete()

        messages.success(
            request,
            f'Deleted {deleted_count} build(s) and {apk_count} APK file(s) older than {days} days.'
        )
        return

    # Show confirmation form
    return modeladmin.cleanup_confirmation_view(request, queryset)

cleanup_old_builds.short_description = 'Clean up old builds'


def export_build_report(modeladmin, request, queryset):
    """Export detailed build report"""
    format_type = request.GET.get('format', 'csv')

    # Gather statistics
    stats = queryset.aggregate(
        total_builds=Count('id'),
        successful_builds=Count('id', filter=Q(status='success')),
        failed_builds=Count('id', filter=Q(status='failed')),
        avg_duration=Avg(
            F('completed_at') - F('started_at'),
            filter=Q(status='success')
        ),
        total_downloads=Sum('download_count')
    )

    if format_type == 'json':
        # JSON format
        builds_data = []
        for build in queryset.select_related('project'):
            builds_data.append({
                'build_number': build.build_number or build.pk,
                'project': build.project.name,
                'version': build.version,
                'status': build.status,
                'platform': build.platform,
                'created_at': build.created_at.isoformat(),
                'started_at': build.started_at.isoformat() if build.started_at else None,
                'completed_at': build.completed_at.isoformat() if build.completed_at else None,
                'duration_seconds': (
                    (build.completed_at - build.started_at).total_seconds()
                    if build.started_at and build.completed_at else None
                ),
                'apk_size_mb': (
                    build.apk_file.size / (1024 * 1024)
                    if build.apk_file else None
                ),
                'download_count': build.download_count,
                'error_message': build.error_message if build.status == 'failed' else None
            })

        report_data = {
            'export_date': timezone.now().isoformat(),
            'statistics': {
                'total_builds': stats['total_builds'],
                'successful_builds': stats['successful_builds'],
                'failed_builds': stats['failed_builds'],
                'success_rate': (
                    stats['successful_builds'] / stats['total_builds'] * 100
                    if stats['total_builds'] > 0 else 0
                ),
                'avg_duration_seconds': (
                    stats['avg_duration'].total_seconds()
                    if stats['avg_duration'] else None
                ),
                'total_downloads': stats['total_downloads'] or 0
            },
            'builds': builds_data
        }

        response = HttpResponse(
            json.dumps(report_data, indent=2),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename="build_report.json"'

    else:
        # CSV format (default)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="build_report.csv"'

        writer = csv.writer(response)

        # Write header
        writer.writerow([
            'Build #', 'Project', 'Version', 'Status', 'Platform',
            'Created At', 'Started At', 'Completed At', 'Duration (min)',
            'APK Size (MB)', 'Downloads', 'Error Message'
        ])

        # Write build data
        for build in queryset.select_related('project'):
            duration = None
            if build.started_at and build.completed_at:
                duration = (build.completed_at - build.started_at).total_seconds() / 60

            apk_size = None
            if build.apk_file:
                try:
                    apk_size = build.apk_file.size / (1024 * 1024)
                except:
                    pass

            writer.writerow([
                build.build_number or build.pk,
                build.project.name,
                build.version,
                build.status,
                build.platform,
                build.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                build.started_at.strftime('%Y-%m-%d %H:%M:%S') if build.started_at else '',
                build.completed_at.strftime('%Y-%m-%d %H:%M:%S') if build.completed_at else '',
                f'{duration:.1f}' if duration else '',
                f'{apk_size:.1f}' if apk_size else '',
                build.download_count,
                build.error_message if build.status == 'failed' else ''
            ])

        # Write summary
        writer.writerow([])
        writer.writerow(['Summary Statistics'])
        writer.writerow(['Total Builds:', stats['total_builds']])
        writer.writerow(['Successful:', stats['successful_builds']])
        writer.writerow(['Failed:', stats['failed_builds']])
        writer.writerow([
            'Success Rate:',
            f"{stats['successful_builds'] / stats['total_builds'] * 100:.1f}%"
            if stats['total_builds'] > 0 else '0%'
        ])
        writer.writerow(['Total Downloads:', stats['total_downloads'] or 0])

    return response

export_build_report.short_description = 'Export build report'


def cancel_running_builds(modeladmin, request, queryset):
    """Cancel all running builds"""
    running_builds = queryset.filter(status='building')

    if not running_builds.exists():
        messages.warning(request, 'No running builds selected.')
        return

    cancelled_count = 0

    for build in running_builds:
        build.status = 'cancelled'
        build.completed_at = timezone.now()
        build.save()

        # Add log entry
        BuildLog.objects.create(
            build=build,
            level='warning',
            message='Build cancelled by admin action'
        )

        cancelled_count += 1

    messages.warning(
        request,
        f'Cancelled {cancelled_count} running build(s).'
    )

cancel_running_builds.short_description = 'Cancel running builds'


def mark_as_success(modeladmin, request, queryset):
    """Mark builds as successful (for testing)"""
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can perform this action.')
        return

    updated = queryset.update(
        status='success',
        completed_at=timezone.now()
    )

    messages.success(request, f'Marked {updated} build(s) as successful.')

mark_as_success.short_description = '[TEST] Mark as success'


def analyze_build_performance(modeladmin, request, queryset):
    """Analyze build performance metrics"""
    # Group by project
    project_stats = {}

    for build in queryset.select_related('project'):
        project_name = build.project.name

        if project_name not in project_stats:
            project_stats[project_name] = {
                'total': 0,
                'success': 0,
                'failed': 0,
                'durations': [],
                'sizes': []
            }

        stats = project_stats[project_name]
        stats['total'] += 1

        if build.status == 'success':
            stats['success'] += 1

            # Calculate duration
            if build.started_at and build.completed_at:
                duration = (build.completed_at - build.started_at).total_seconds()
                stats['durations'].append(duration)

            # Get APK size
            if build.apk_file:
                try:
                    stats['sizes'].append(build.apk_file.size)
                except:
                    pass

        elif build.status == 'failed':
            stats['failed'] += 1

    # Generate report
    report_lines = [
        "Build Performance Analysis",
        f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total Builds Analyzed: {queryset.count()}",
        "",
        "Performance by Project:",
        "-" * 80
    ]

    for project, stats in sorted(project_stats.items()):
        success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
        avg_duration = sum(stats['durations']) / len(stats['durations']) if stats['durations'] else 0
        avg_size = sum(stats['sizes']) / len(stats['sizes']) if stats['sizes'] else 0

        report_lines.extend([
            f"\nProject: {project}",
            f"  Total Builds: {stats['total']}",
            f"  Successful: {stats['success']}",
            f"  Failed: {stats['failed']}",
            f"  Success Rate: {success_rate:.1f}%",
            f"  Avg Duration: {avg_duration/60:.1f} minutes" if avg_duration else "  Avg Duration: N/A",
            f"  Avg APK Size: {avg_size/1024/1024:.1f} MB" if avg_size else "  Avg APK Size: N/A"
        ])

    # Return as text file
    response = HttpResponse(
        '\n'.join(report_lines),
        content_type='text/plain'
    )
    response['Content-Disposition'] = 'attachment; filename="build_performance_analysis.txt"'

    return response

analyze_build_performance.short_description = 'Analyze performance'