import django_filters
from django.db.models import Q
from .models import FlutterProject, Screen, ComponentTemplate


class FlutterProjectFilter(django_filters.FilterSet):
    """Filter for FlutterProject model"""
    name = django_filters.CharFilter(lookup_expr='icontains')
    package_name = django_filters.CharFilter(lookup_expr='icontains')
    has_version = django_filters.BooleanFilter(
        field_name='app_version',
        lookup_expr='isnull',
        exclude=True,
        label='Has Version'
    )
    has_screens = django_filters.BooleanFilter(
        method='filter_has_screens',
        label='Has Screens'
    )
    has_builds = django_filters.BooleanFilter(
        method='filter_has_builds',
        label='Has Builds'
    )
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        label='Created After'
    )
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        label='Created Before'
    )
    language = django_filters.CharFilter(
        field_name='supported_languages__lang',
        label='Supported Language'
    )

    class Meta:
        model = FlutterProject
        fields = [
            'name', 'package_name', 'has_version',
            'has_screens', 'has_builds', 'created_after',
            'created_before', 'language'
        ]

    def filter_has_screens(self, queryset, name, value):
        """Filter projects that have screens"""
        if value:
            return queryset.filter(screen_set__isnull=False).distinct()
        return queryset.filter(screen_set__isnull=True)

    def filter_has_builds(self, queryset, name, value):
        """Filter projects that have builds"""
        if value:
            return queryset.filter(build_set__isnull=False).distinct()
        return queryset.filter(build_set__isnull=True)


class ScreenFilter(django_filters.FilterSet):
    """Filter for Screen model"""
    name = django_filters.CharFilter(lookup_expr='icontains')
    route = django_filters.CharFilter(lookup_expr='icontains')
    is_home = django_filters.BooleanFilter()
    project = django_filters.NumberFilter()
    project_name = django_filters.CharFilter(
        field_name='project__name',
        lookup_expr='icontains'
    )

    class Meta:
        model = Screen
        fields = ['name', 'route', 'is_home', 'project', 'project_name']


class ComponentTemplateFilter(django_filters.FilterSet):
    """Filter for ComponentTemplate model"""
    name = django_filters.CharFilter(lookup_expr='icontains')
    category = django_filters.CharFilter(lookup_expr='exact')
    flutter_widget = django_filters.CharFilter(lookup_expr='icontains')
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = ComponentTemplate
        fields = ['name', 'category', 'flutter_widget', 'is_active']