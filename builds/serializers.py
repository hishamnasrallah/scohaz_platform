from rest_framework import serializers
from django.core.files.base import ContentFile
from .models import Build, BuildLog
from projects.models import FlutterProject
import re


class BuildLogSerializer(serializers.ModelSerializer):
    """Serializer for BuildLog model"""
    class Meta:
        model = BuildLog
        fields = ['id', 'message', 'level', 'timestamp']
        read_only_fields = ['id', 'timestamp']


class BuildSerializer(serializers.ModelSerializer):
    """Serializer for Build model"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    package_name = serializers.CharField(source='project.package_name', read_only=True)
    apk_size = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Build
        fields = [
            'id', 'project', 'project_name', 'package_name', 'version',
            'status', 'apk_file', 'download_url', 'apk_size', 'build_log',
            'duration', 'created_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'status', 'apk_file', 'build_log',
            'created_at', 'completed_at'
        ]

    def get_apk_size(self, obj):
        """Get APK file size in MB"""
        if obj.apk_file:
            try:
                size_mb = obj.apk_file.size / (1024 * 1024)
                return f"{size_mb:.2f} MB"
            except:
                return None
        return None

    def get_duration(self, obj):
        """Get build duration in seconds"""
        if obj.completed_at and obj.created_at:
            duration = (obj.completed_at - obj.created_at).total_seconds()
            return f"{duration:.1f} seconds"
        return None

    def get_download_url(self, obj):
        """Get download URL for APK"""
        if obj.apk_file and obj.status == 'success':
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.apk_file.url)
        return None

    def validate_version(self, value):
        """Validate version format"""
        pattern = r'^\d+\.\d+\.\d+$'
        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "Version must follow semantic versioning (e.g., 1.0.0)"
            )
        return value


class BuildListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for build lists"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    duration = serializers.SerializerMethodField()

    class Meta:
        model = Build
        fields = [
            'id', 'project_name', 'version', 'status',
            'duration', 'created_at'
        ]

    def get_duration(self, obj):
        """Get build duration"""
        if obj.completed_at and obj.created_at:
            duration = (obj.completed_at - obj.created_at).total_seconds()
            return f"{duration:.1f}s"
        return None


class TriggerBuildSerializer(serializers.Serializer):
    """Serializer for triggering a new build"""
    project_id = serializers.IntegerField()
    version = serializers.CharField(max_length=20)
    build_type = serializers.ChoiceField(
        choices=['debug', 'release'],
        default='release'
    )

    def validate_project_id(self, value):
        """Validate project exists and belongs to user"""
        request = self.context.get('request')
        project = FlutterProject.objects.filter(
            id=value,
            user=request.user
        ).first()

        if not project:
            raise serializers.ValidationError("Project not found or access denied")

        # Check if project has screens
        if not project.screen_set.exists():
            raise serializers.ValidationError("Project has no screens to build")

        # Check for active build
        active_build = Build.objects.filter(
            project_id=value,
            status__in=['pending', 'building']
        ).exists()

        if active_build:
            raise serializers.ValidationError(
                "Another build is already in progress for this project"
            )

        return value

    def validate_version(self, value):
        """Validate version format"""
        pattern = r'^\d+\.\d+\.\d+$'
        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "Version must follow semantic versioning (e.g., 1.0.0)"
            )
        return value


class BuildStatusSerializer(serializers.Serializer):
    """Serializer for build status updates"""
    status = serializers.ChoiceField(
        choices=['pending', 'building', 'success', 'failed']
    )
    message = serializers.CharField(required=False)
    progress = serializers.IntegerField(min_value=0, max_value=100, required=False)


class BuildStatsSerializer(serializers.Serializer):
    """Serializer for build statistics"""
    total_builds = serializers.IntegerField()
    successful_builds = serializers.IntegerField()
    failed_builds = serializers.IntegerField()
    average_build_time = serializers.FloatField()
    total_apk_size = serializers.FloatField()
    builds_by_status = serializers.DictField()
    builds_by_project = serializers.ListField()
    recent_builds = BuildListSerializer(many=True)