import django_filters
from django.db.models import Q
from .models import Build, BuildLog


class BuildFilter(django_filters.FilterSet):
    """Filter for Build model"""
    project = django_filters.NumberFilter()
    project_name = django_filters.CharFilter(
        field_name='project__name',
        lookup_expr='icontains',
        label='Project Name'
    )
    status = django_filters.ChoiceFilter(
        choices=[
            ('pending', 'Pending'),
            ('building', 'Building'),
            ('success', 'Success'),
            ('failed', 'Failed')
        ]
    )
    version = django_filters.CharFilter(lookup_expr='icontains')
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
    has_apk = django_filters.BooleanFilter(
        method='filter_has_apk',
        label='Has APK File'
    )
    build_time = django_filters.NumberFilter(
        method='filter_build_time',
        label='Build Time (seconds)'
    )

    class Meta:
        model = Build
        fields = [
            'project', 'project_name', 'status', 'version',
            'created_after', 'created_before', 'has_apk', 'build_time'
        ]

    def filter_has_apk(self, queryset, name, value):
        """Filter builds that have APK files"""
        if value:
            return queryset.exclude(apk_file='')
        return queryset.filter(apk_file='')

    def filter_build_time(self, queryset, name, value):
        """Filter by build duration in seconds"""
        # This would require annotating the queryset with duration
        # For now, return the original queryset
        return queryset


class BuildLogFilter(django_filters.FilterSet):
    """Filter for BuildLog model"""
    build = django_filters.NumberFilter()
    level = django_filters.ChoiceFilter(
        choices=[
            ('DEBUG', 'Debug'),
            ('INFO', 'Info'),
            ('WARNING', 'Warning'),
            ('ERROR', 'Error')
        ]
    )
    message = django_filters.CharFilter(lookup_expr='icontains')
    timestamp_after = django_filters.DateTimeFilter(
        field_name='timestamp',
        lookup_expr='gte'
    )
    timestamp_before = django_filters.DateTimeFilter(
        field_name='timestamp',
        lookup_expr='lte'
    )

    class Meta:
        model = BuildLog
        fields = ['build', 'level', 'message', 'timestamp_after', 'timestamp_before']