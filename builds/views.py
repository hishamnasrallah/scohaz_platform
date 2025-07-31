from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.http import FileResponse, Http404
from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from .models import Build, BuildLog
from .serializers import (
    BuildSerializer, BuildListSerializer, BuildLogSerializer,
    TriggerBuildSerializer, BuildStatusSerializer, BuildStatsSerializer
)
from .filters import BuildFilter
from .tasks import execute_flutter_build
from projects.models import FlutterProject
from projects.permissions import IsProjectOwner


class BuildViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Build read operations"""
    permission_classes = [IsAuthenticated, IsProjectOwner]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = BuildFilter
    ordering_fields = ['created_at', 'status', 'version']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter builds by user's projects"""
        return Build.objects.filter(
            project__user=self.request.user
        ).select_related('project')

    def get_serializer_class(self):
        """Use different serializers for list and detail views"""
        if self.action == 'list':
            return BuildListSerializer
        return BuildSerializer

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download APK file"""
        build = self.get_object()

        if build.status != 'success' or not build.apk_file:
            raise Http404("APK file not available")

        try:
            # Open file and return as response
            file_handle = build.apk_file.open()
            response = FileResponse(
                file_handle,
                content_type='application/vnd.android.package-archive'
            )
            response['Content-Disposition'] = f'attachment; filename="{build.project.name}-{build.version}.apk"'
            return response
        except Exception as e:
            raise Http404(f"Error downloading file: {str(e)}")

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """Get build logs"""
        build = self.get_object()
        logs = build.buildlog_set.order_by('timestamp')

        # Optional level filter
        level = request.query_params.get('level', None)
        if level:
            logs = logs.filter(level=level)

        serializer = BuildLogSerializer(logs, many=True)
        return Response({
            'build_id': build.id,
            'status': build.status,
            'logs': serializer.data
        })

    @action(detail=True, methods=['delete'])
    def cancel(self, request, pk=None):
        """Cancel a pending or building build"""
        build = self.get_object()

        if build.status not in ['pending', 'building']:
            return Response(
                {'error': 'Can only cancel pending or building builds'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update build status
        build.status = 'failed'
        build.build_log = 'Build cancelled by user'
        build.completed_at = timezone.now()
        build.save()

        # Add log entry
        BuildLog.objects.create(
            build=build,
            message='Build cancelled by user',
            level='ERROR'
        )

        return Response({'message': 'Build cancelled successfully'})


class TriggerBuildAPIView(APIView):
    """API view for triggering new builds"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Trigger a new build"""
        serializer = TriggerBuildSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            data = serializer.validated_data

            # Get project
            project = get_object_or_404(
                FlutterProject,
                id=data['project_id'],
                user=request.user
            )

            # Create build record
            build = Build.objects.create(
                project=project,
                version=data['version'],
                status='pending',
                build_log='Build queued'
            )

            # Add initial log
            BuildLog.objects.create(
                build=build,
                message='Build created and queued for processing',
                level='INFO'
            )

            # Trigger async build task
            execute_flutter_build.delay(
                build_id=build.id,
                build_type=data['build_type']
            )

            # Return build details
            build_serializer = BuildSerializer(
                build,
                context={'request': request}
            )

            return Response(
                build_serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BuildStatsAPIView(APIView):
    """API view for build statistics"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get build statistics for user's projects"""
        # Base queryset
        builds = Build.objects.filter(project__user=request.user)

        # Calculate statistics
        stats = builds.aggregate(
            total_builds=Count('id'),
            successful_builds=Count('id', filter=Q(status='success')),
            failed_builds=Count('id', filter=Q(status='failed')),
            avg_duration=Avg(
                timezone.now() - models.F('created_at'),
                filter=Q(completed_at__isnull=False)
            ),
            total_size=Sum('apk_file__size', filter=Q(status='success'))
        )

        # Builds by status
        builds_by_status = builds.values('status').annotate(
            count=Count('id')
        ).order_by('status')

        status_dict = {
            item['status']: item['count']
            for item in builds_by_status
        }

        # Builds by project
        builds_by_project = builds.values(
            'project__id', 'project__name'
        ).annotate(
            total=Count('id'),
            successful=Count('id', filter=Q(status='success'))
        ).order_by('-total')[:10]

        # Recent builds
        recent_builds = builds.order_by('-created_at')[:10]

        # Prepare response
        response_data = {
            'total_builds': stats['total_builds'] or 0,
            'successful_builds': stats['successful_builds'] or 0,
            'failed_builds': stats['failed_builds'] or 0,
            'average_build_time': stats['avg_duration'].total_seconds() if stats['avg_duration'] else 0,
            'total_apk_size': stats['total_size'] or 0,
            'builds_by_status': status_dict,
            'builds_by_project': list(builds_by_project),
            'recent_builds': BuildListSerializer(recent_builds, many=True).data
        }

        stats_serializer = BuildStatsSerializer(data=response_data)
        if stats_serializer.is_valid():
            return Response(stats_serializer.data)

        return Response(
            stats_serializer.errors,
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class BuildStatusWebSocketView(APIView):
    """API view for build status updates (placeholder for WebSocket)"""
    permission_classes = [IsAuthenticated]

    def get(self, request, build_id):
        """Get current build status"""
        build = get_object_or_404(
            Build,
            id=build_id,
            project__user=request.user
        )

        # Get latest logs
        recent_logs = build.buildlog_set.order_by('-timestamp')[:5]

        return Response({
            'build_id': build.id,
            'status': build.status,
            'progress': self._calculate_progress(build),
            'recent_logs': BuildLogSerializer(recent_logs, many=True).data
        })

    def _calculate_progress(self, build):
        """Calculate build progress based on logs"""
        if build.status == 'pending':
            return 0
        elif build.status == 'success':
            return 100
        elif build.status == 'failed':
            return 0
        else:
            # Estimate based on log entries
            total_steps = 10  # Approximate build steps
            completed_steps = build.buildlog_set.filter(
                level='INFO'
            ).count()
            return min(int((completed_steps / total_steps) * 100), 90)