# File: builds/serializers.py

from rest_framework import serializers
from builds.models import Build, BuildLog
from django.utils import timezone


class BuildLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = BuildLog
        fields = ['id', 'timestamp', 'level', 'stage', 'message']
        read_only_fields = ['id', 'timestamp']


class BuildSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    project_package = serializers.CharField(source='project.package_name', read_only=True)
    apk_url = serializers.SerializerMethodField()
    duration_display = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    build_type_display = serializers.CharField(source='get_build_type_display', read_only=True)
    logs_count = serializers.SerializerMethodField()

    class Meta:
        model = Build
        fields = [
            'id', 'project', 'project_name', 'project_package',
            'status', 'status_display', 'build_type', 'build_type_display',
            'version_number', 'build_number', 'apk_file', 'apk_url',
            'apk_size', 'flutter_version', 'dart_version',
            'error_message', 'created_at', 'started_at', 'completed_at',
            'duration_seconds', 'duration_display', 'logs_count'
        ]
        read_only_fields = [
            'status', 'apk_file', 'apk_size', 'flutter_version',
            'dart_version', 'error_message', 'started_at',
            'completed_at', 'duration_seconds'
        ]

    def get_apk_url(self, obj):
        if obj.apk_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.apk_file.url)
        return None

    def get_duration_display(self, obj):
        """Format duration in human-readable format"""
        if obj.duration_seconds:
            minutes, seconds = divmod(obj.duration_seconds, 60)
            if minutes > 0:
                return f"{minutes}m {seconds}s"
            return f"{seconds}s"
        return None

    def get_logs_count(self, obj):
        """Get the number of log entries"""
        return obj.logs.count()


class BuildCreateSerializer(serializers.Serializer):
    """Serializer for creating builds"""
    project_id = serializers.IntegerField(required=True)
    build_type = serializers.ChoiceField(
        choices=['debug', 'release', 'profile'],
        default='release'
    )
    version_number = serializers.CharField(default='1.0.0')
    build_number = serializers.IntegerField(default=1)

    def validate_version_number(self, value):
        """Validate version number format"""
        import re
        if not re.match(r'^\d+\.\d+\.\d+$', value):
            raise serializers.ValidationError(
                "Version number must be in format X.Y.Z (e.g., 1.0.0)"
            )
        return value


class BuildStatisticsSerializer(serializers.Serializer):
    """Serializer for build statistics"""
    total_builds = serializers.IntegerField()
    successful_builds = serializers.IntegerField()
    failed_builds = serializers.IntegerField()
    pending_builds = serializers.IntegerField()
    building = serializers.IntegerField()
    cancelled_builds = serializers.IntegerField()
    average_build_time = serializers.FloatField(allow_null=True)