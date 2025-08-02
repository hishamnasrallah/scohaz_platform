# File: builds/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import FileResponse, Http404
from django.conf import settings
from builds.models import Build, BuildLog
from projects.models import FlutterProject
from builds.serializers import BuildSerializer, BuildLogSerializer
from builds.tasks import process_build_task
import os


class BuildViewSet(viewsets.ModelViewSet):
    serializer_class = BuildSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Build.objects.filter(project__user=self.request.user)

        # Filter by project if specified
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        # Filter by status if specified
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def create(self, request, *args, **kwargs):
        """Create a new build"""
        project_id = request.data.get('project_id')
        build_type = request.data.get('build_type', 'release')

        if not project_id:
            return Response(
                {'error': 'project_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get project
        project = get_object_or_404(
            FlutterProject,
            id=project_id,
            user=request.user
        )

        # Check for pending builds
        pending_builds = Build.objects.filter(
            project=project,
            status__in=['pending', 'building']
        ).count()

        if pending_builds > 0:
            return Response(
                {'error': 'Another build is already in progress for this project'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate build type
        if build_type not in ['debug', 'release', 'profile']:
            return Response(
                {'error': 'Invalid build_type. Must be debug, release, or profile'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # using celery
        # # Create build
        # build = Build.objects.create(
        #     project=project,
        #     build_type=build_type,
        #     version_number=request.data.get('version_number', '1.0.0'),
        #     build_number=request.data.get('build_number', 1)
        # )
        #
        # # Queue build task
        # process_build_task.delay(build.id)
        #
        # serializer = self.get_serializer(build)
        # return Response(serializer.data, status=status.HTTP_201_CREATED)



        # without celery 
        # Create build
        build = Build.objects.create(
            project=project,
            build_type=build_type,
            version_number=request.data.get('version_number', '1.0.0'),
            build_number=request.data.get('build_number', 1)
        )

        # Run build synchronously for testing (without Celery)
        from builds.services.build_service import BuildService
        service = BuildService()
        service.start_build(build)

        # Refresh build instance to get updated status
        build.refresh_from_db()

        serializer = self.get_serializer(build)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    @action(detail=True)
    def logs(self, request, pk=None):
        """Get build logs"""
        build = self.get_object()

        # Optional filtering by level
        level = request.query_params.get('level')
        logs = BuildLog.objects.filter(build=build)

        if level:
            logs = logs.filter(level=level)

        serializer = BuildLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=True)
    def download(self, request, pk=None):
        """Download APK file"""
        build = self.get_object()

        if build.status != 'success' or not build.apk_file:
            return Response(
                {'error': 'APK not available'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            return FileResponse(
                build.apk_file.open('rb'),
                as_attachment=True,
                filename=os.path.basename(build.apk_file.name)
            )
        except FileNotFoundError:
            raise Http404("APK file not found")

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a pending build"""
        build = self.get_object()

        if build.status not in ['pending', 'building']:
            return Response(
                {'error': 'Build cannot be cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )

        build.status = 'cancelled'
        build.error_message = 'Build cancelled by user'
        build.save()

        return Response({'status': 'Build cancelled'})

    @action(detail=False)
    def statistics(self, request):
        """Get build statistics for the user"""
        builds = self.get_queryset()

        stats = {
            'total_builds': builds.count(),
            'successful_builds': builds.filter(status='success').count(),
            'failed_builds': builds.filter(status='failed').count(),
            'pending_builds': builds.filter(status='pending').count(),
            'building': builds.filter(status='building').count(),
            'cancelled_builds': builds.filter(status='cancelled').count(),
            'average_build_time': None,
        }

        # Calculate average build time for successful builds
        successful_builds = builds.filter(
            status='success',
            duration_seconds__isnull=False
        )

        if successful_builds.exists():
            total_duration = sum(b.duration_seconds for b in successful_builds)
            stats['average_build_time'] = total_duration / successful_builds.count()

        return Response(stats)

    @action(detail=False)
    def recent(self, request):
        """Get recent builds"""
        limit = int(request.query_params.get('limit', 10))
        builds = self.get_queryset()[:limit]
        serializer = self.get_serializer(builds, many=True)
        return Response(serializer.data)