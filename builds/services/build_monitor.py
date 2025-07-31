"""
Build monitoring service for tracking build progress and status.
"""

import logging
from datetime import timedelta
from typing import Dict, List, Optional

from django.utils import timezone
from django.db.models import Count, Avg, Q

from builds.models import Build, BuildLog

logger = logging.getLogger(__name__)


class BuildMonitor:
    """Service for monitoring build status and progress."""

    def get_build_status(self, build: Build) -> Dict:
        """
        Get detailed build status information.

        Args:
            build: Build model instance

        Returns:
            Dictionary with build status details
        """
        # Calculate duration
        duration = None
        if build.started_at:
            end_time = build.completed_at or timezone.now()
            duration = (end_time - build.started_at).total_seconds()

        # Get recent logs
        recent_logs = BuildLog.objects.filter(
            build=build
        ).order_by('-timestamp')[:10]

        # Prepare response
        status_data = {
            'id': build.id,
            'project': {
                'id': build.project.id,
                'name': build.project.name,
                'package_name': build.project.package_name
            },
            'status': build.status,
            'version': build.version,
            'build_type': build.build_type,
            'created_at': build.created_at.isoformat() if build.created_at else None,
            'started_at': build.started_at.isoformat() if build.started_at else None,
            'completed_at': build.completed_at.isoformat() if build.completed_at else None,
            'duration_seconds': duration,
            'duration_display': self._format_duration(duration) if duration else None,
            'apk_file': {
                'url': build.apk_file.url if build.apk_file else None,
                'size': build.apk_size,
                'size_display': self._format_file_size(build.apk_size) if build.apk_size else None
            },
            'error_message': build.error_message,
            'logs': [
                {
                    'timestamp': log.timestamp.isoformat(),
                    'level': log.level,
                    'message': log.message
                } for log in recent_logs
            ],
            'can_retry': build.status in ['failed', 'cancelled'],
            'can_download': build.status == 'success' and build.apk_file
        }

        return status_data

    def get_project_build_stats(self, project_id: int) -> Dict:
        """
        Get build statistics for a project.

        Args:
            project_id: Project ID

        Returns:
            Dictionary with build statistics
        """
        builds = Build.objects.filter(project_id=project_id)

        # Count by status
        status_counts = builds.values('status').annotate(
            count=Count('id')
        ).order_by('status')

        # Average build time for successful builds
        avg_build_time = builds.filter(
            status='success',
            started_at__isnull=False,
            completed_at__isnull=False
        ).aggregate(
            avg_duration=Avg(
                timezone.now() - timezone.now()  # Placeholder for duration calculation
            )
        )

        # Recent builds
        recent_builds = builds.order_by('-created_at')[:5]

        stats = {
            'total_builds': builds.count(),
            'status_breakdown': {
                item['status']: item['count']
                for item in status_counts
            },
            'success_rate': self._calculate_success_rate(builds),
            'average_build_time': avg_build_time['avg_duration'],
            'recent_builds': [
                {
                    'id': build.id,
                    'version': build.version,
                    'status': build.status,
                    'created_at': build.created_at.isoformat()
                } for build in recent_builds
            ]
        }

        return stats

    def get_system_stats(self) -> Dict:
        """
        Get overall system build statistics.

        Returns:
            Dictionary with system statistics
        """
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)

        # Get build counts
        total_builds = Build.objects.count()
        builds_24h = Build.objects.filter(created_at__gte=last_24h).count()
        builds_7d = Build.objects.filter(created_at__gte=last_7d).count()

        # Active builds
        active_builds = Build.objects.filter(
            status__in=['pending', 'building']
        ).count()

        # Success rate
        success_rate_24h = self._calculate_success_rate(
            Build.objects.filter(created_at__gte=last_24h)
        )

        # Queue status
        queue_size = Build.objects.filter(status='pending').count()

        stats = {
            'total_builds': total_builds,
            'builds_last_24h': builds_24h,
            'builds_last_7d': builds_7d,
            'active_builds': active_builds,
            'queue_size': queue_size,
            'success_rate_24h': success_rate_24h,
            'system_status': self._get_system_status(active_builds, queue_size)
        }

        return stats

    def get_build_queue(self) -> List[Dict]:
        """
        Get current build queue.

        Returns:
            List of queued builds
        """
        queued_builds = Build.objects.filter(
            status='pending'
        ).order_by('created_at')

        queue = []
        for position, build in enumerate(queued_builds, 1):
            queue.append({
                'position': position,
                'build_id': build.id,
                'project_name': build.project.name,
                'version': build.version,
                'created_at': build.created_at.isoformat(),
                'wait_time': self._format_duration(
                    (timezone.now() - build.created_at).total_seconds()
                )
            })

        return queue

    def check_stale_builds(self) -> List[Build]:
        """
        Check for stale builds that may need cleanup.

        Returns:
            List of stale Build instances
        """
        # Builds that have been "building" for too long
        stale_threshold = timezone.now() - timedelta(hours=1)

        stale_builds = Build.objects.filter(
            status='building',
            started_at__lt=stale_threshold
        )

        return list(stale_builds)

    def _calculate_success_rate(self, builds) -> float:
        """Calculate success rate for a queryset of builds."""
        total = builds.filter(
            status__in=['success', 'failed']
        ).count()

        if total == 0:
            return 0.0

        successful = builds.filter(status='success').count()
        return (successful / total) * 100

    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human-readable string."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            seconds = int(seconds % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in bytes to human-readable string."""
        if not size_bytes:
            return "0 B"

        units = ['B', 'KB', 'MB', 'GB']
        size = float(size_bytes)
        unit_index = 0

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        return f"{size:.1f} {units[unit_index]}"

    def _get_system_status(self, active_builds: int, queue_size: int) -> str:
        """Determine overall system status."""
        if active_builds == 0 and queue_size == 0:
            return "idle"
        elif queue_size > 10:
            return "busy"
        elif active_builds > 5:
            return "high_load"
        else:
            return "normal"