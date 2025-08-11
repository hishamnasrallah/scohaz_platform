from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import FileResponse, Http404
from simple_builds.models import Build, BuildLog
from simple_project.models import FlutterProject
from simple_builds.serializers import (
    BuildSerializer,
    BuildLogSerializer,
    BuildCreateSerializer
)
from simple_builds.services.build_service import BuildService
import os


class BuildViewSet(viewsets.ModelViewSet):
    serializer_class = BuildSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Build.objects.filter(project__user=self.request.user)

        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def create(self, request, *args, **kwargs):
        """Create a new build"""
        serializer = BuildCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project_id = serializer.validated_data['project_id']

        project = get_object_or_404(
            FlutterProject,
            id=project_id,
            user=request.user
        )

        # Check for pending builds
        if Build.objects.filter(
                project=project,
                status__in=['pending', 'building']
        ).exists():
            return Response(
                {'error': 'Another build is already in progress for this project'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create build
        build = Build.objects.create(
            project=project,
            build_type=serializer.validated_data['build_type'],
            version_number=serializer.validated_data['version_number'],
            build_number=serializer.validated_data['build_number']
        )

        # Start build process
        service = BuildService()
        service.start_build(build)

        # Refresh and return
        build.refresh_from_db()
        response_serializer = self.get_serializer(build)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True)
    def logs(self, request, pk=None):
        """Get build logs"""
        build = self.get_object()

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
        """Get build statistics"""
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

        successful_builds = builds.filter(
            status='success',
            duration_seconds__isnull=False
        )

        if successful_builds.exists():
            total_duration = sum(b.duration_seconds for b in successful_builds)
            stats['average_build_time'] = total_duration / successful_builds.count()

        return Response(stats)