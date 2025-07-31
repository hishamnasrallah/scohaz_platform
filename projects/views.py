from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import FlutterProject, Screen, ComponentTemplate
from .serializers import (
    FlutterProjectSerializer, FlutterProjectListSerializer,
    ScreenSerializer, ComponentTemplateSerializer,
    SetVersionSerializer, AddLanguageSerializer
)
from .filters import FlutterProjectFilter
from .permissions import IsProjectOwner
from version.models import Version, LocalVersion


class FlutterProjectViewSet(viewsets.ModelViewSet):
    """ViewSet for FlutterProject CRUD operations"""
    permission_classes = [IsAuthenticated, IsProjectOwner]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = FlutterProjectFilter
    search_fields = ['name', 'package_name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter projects by current user"""
        return FlutterProject.objects.filter(user=self.request.user) \
            .select_related('app_version', 'user') \
            .prefetch_related('supported_languages', 'screen_set', 'build_set')

    def get_serializer_class(self):
        """Use different serializers for list and detail views"""
        if self.action == 'list':
            return FlutterProjectListSerializer
        return FlutterProjectSerializer

    def perform_create(self, serializer):
        """Set the user when creating a project"""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], serializer_class=SetVersionSerializer)
    def set_version(self, request, pk=None):
        """Create version entry for generated Flutter app"""
        project = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            data = serializer.validated_data

            # Create or update version
            version, created = Version.objects.update_or_create(
                defaults={
                    'version_number': data['version_number'],
                    'operating_system': data['operating_system'],
                    '_environment': '1',  # Production
                    'active_ind': True
                }
            )

            project.app_version = version
            project.save()

            return Response({
                'message': f'Version {version.version_number} {"created" if created else "updated"}',
                'version': {
                    'id': version.id,
                    'version_number': version.version_number,
                    'operating_system': version.operating_system
                }
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], serializer_class=AddLanguageSerializer)
    def add_language(self, request, pk=None):
        """Add language support using LocalVersion"""
        project = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            lang_code = serializer.validated_data['language']

            local_version = LocalVersion.objects.filter(
                lang=lang_code,
                active_ind=True
            ).first()

            if local_version:
                if project.supported_languages.filter(id=local_version.id).exists():
                    return Response(
                        {'error': f'Language {lang_code} already added'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                project.supported_languages.add(local_version)

                return Response({
                    'message': f'Language {lang_code} added successfully',
                    'language': {
                        'id': local_version.id,
                        'lang': local_version.lang
                    }
                })

            return Response(
                {'error': 'Language not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'])
    def remove_language(self, request, pk=None):
        """Remove language support"""
        project = self.get_object()
        lang_code = request.data.get('language')

        if not lang_code:
            return Response(
                {'error': 'Language code required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        local_version = project.supported_languages.filter(lang=lang_code).first()

        if local_version:
            project.supported_languages.remove(local_version)
            return Response({
                'message': f'Language {lang_code} removed successfully'
            })

        return Response(
            {'error': f'Language {lang_code} not found in project'},
            status=status.HTTP_404_NOT_FOUND
        )

    @action(detail=True, methods=['get'])
    def available_languages(self, request, pk=None):
        """Get languages available to add to the project"""
        project = self.get_object()

        # Get active languages not already in project
        existing_langs = project.supported_languages.values_list('lang', flat=True)
        available = LocalVersion.objects.filter(
            active_ind=True
        ).exclude(lang__in=existing_langs)

        languages = [
            {'lang': lv.lang, 'id': lv.id}
            for lv in available
        ]

        return Response({
            'available_languages': languages,
            'supported_languages': list(existing_langs)
        })

    @action(detail=True, methods=['get', 'post'])
    def screens(self, request, pk=None):
        """Get or create screens for a project"""
        project = self.get_object()

        if request.method == 'GET':
            screens = project.screen_set.all()
            serializer = ScreenSerializer(screens, many=True)
            return Response(serializer.data)

        elif request.method == 'POST':
            serializer = ScreenSerializer(data=request.data)
            if serializer.is_valid():
                # Check if making this the home screen
                if serializer.validated_data.get('is_home', False):
                    # Unset any existing home screen
                    project.screen_set.update(is_home=False)

                serializer.save(project=project)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ScreenViewSet(viewsets.ModelViewSet):
    """ViewSet for Screen CRUD operations"""
    serializer_class = ScreenSerializer
    permission_classes = [IsAuthenticated, IsProjectOwner]

    def get_queryset(self):
        """Filter screens by user's projects"""
        return Screen.objects.filter(
            project__user=self.request.user
        ).select_related('project')

    def perform_update(self, serializer):
        """Handle home screen updates"""
        if serializer.validated_data.get('is_home', False):
            # Unset any existing home screen for this project
            Screen.objects.filter(
                project=serializer.instance.project
            ).exclude(id=serializer.instance.id).update(is_home=False)

        serializer.save()


class ComponentTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for ComponentTemplate read operations"""
    serializer_class = ComponentTemplateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name', 'flutter_widget']
    ordering_fields = ['name', 'category', 'created_at']
    ordering = ['category', 'name']

    def get_queryset(self):
        """Get active component templates"""
        queryset = ComponentTemplate.objects.filter(is_active=True)

        # Optional category filter
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category=category)

        return queryset

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get available component categories"""
        categories = ComponentTemplate.objects.filter(
            is_active=True
        ).values_list('category', flat=True).distinct()

        return Response({
            'categories': list(categories)
        })