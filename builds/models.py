import os
from django.db import models
from django.utils import timezone
from projects.models import FlutterProject
from builder.models import GenerationConfig


def build_upload_path(instance, filename):
    """Generate upload path for APK files"""
    # Format: builds/project_id/timestamp_filename
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    return f'builds/{instance.project.id}/{timestamp}_{filename}'


class Build(models.Model):
    """Tracks Flutter app build jobs and their status"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('generating', 'Generating Code'),
        ('building', 'Building APK'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    BUILD_TYPE_CHOICES = [
        ('debug', 'Debug'),
        ('release', 'Release'),
        ('profile', 'Profile'),
    ]

    project = models.ForeignKey(
        FlutterProject,
        on_delete=models.CASCADE,
        related_name='builds',
        help_text="The project being built"
    )

    # Build configuration
    build_type = models.CharField(
        max_length=20,
        choices=BUILD_TYPE_CHOICES,
        default='debug',
        help_text="Type of build to generate"
    )
    generation_config = models.ForeignKey(
        GenerationConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Code generation configuration used"
    )
    build_log = models.TextField(
        blank=True,
        help_text="Complete build output log"
    )
    # Build status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current build status"
    )
    progress = models.IntegerField(
        default=0,
        help_text="Build progress percentage (0-100)"
    )

    # Version information
    version_number = models.CharField(
        max_length=20,
        default='1.0.0',
        help_text="App version number"
    )
    build_number = models.IntegerField(
        default=1,
        help_text="Build number (incremental)"
    )

    # Output files
    apk_file = models.FileField(
        upload_to=build_upload_path,
        null=True,
        blank=True,
        help_text="Generated APK file"
    )
    apk_size = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="APK file size in bytes"
    )

    # Build metadata
    flutter_version = models.CharField(
        max_length=50,
        blank=True,
        help_text="Flutter SDK version used"
    )
    dart_version = models.CharField(
        max_length=50,
        blank=True,
        help_text="Dart SDK version used"
    )

    # Error tracking
    error_message = models.TextField(
        blank=True,
        help_text="Error message if build failed"
    )

    # Timing information
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the build started"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the build completed"
    )
    duration_seconds = models.IntegerField(
        null=True,
        blank=True,
        help_text="Build duration in seconds"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"{self.project.name} - Build #{self.build_number} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        # Calculate duration if completed
        if self.started_at and self.completed_at and not self.duration_seconds:
            delta = self.completed_at - self.started_at
            self.duration_seconds = int(delta.total_seconds())

        # Set APK size if file exists
        if self.apk_file and not self.apk_size:
            try:
                self.apk_size = self.apk_file.size
            except:
                pass

        super().save(*args, **kwargs)

    @property
    def is_complete(self):
        """Check if build is in a terminal state"""
        return self.status in ['success', 'failed', 'cancelled']

    @property
    def is_running(self):
        """Check if build is currently running"""
        return self.status in ['preparing', 'generating', 'building']


class BuildLog(models.Model):
    """Detailed log entries for build processes"""
    LOG_LEVEL_CHOICES = [
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]

    build = models.ForeignKey(
        Build,
        on_delete=models.CASCADE,
        related_name='logs',
        help_text="The build this log entry belongs to"
    )

    # Log entry details
    level = models.CharField(
        max_length=10,
        choices=LOG_LEVEL_CHOICES,
        default='info',
        help_text="Log level"
    )
    stage = models.CharField(
        max_length=50,
        help_text="Build stage (e.g., 'code_generation', 'flutter_build')"
    )
    message = models.TextField(
        help_text="Log message content"
    )

    # Additional context
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional structured log data"
    )

    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['build', 'created_at']
        indexes = [
            models.Index(fields=['build', 'level']),
        ]

    def __str__(self):
        return f"{self.build} - {self.get_level_display()}: {self.message[:50]}"