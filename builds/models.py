# File: builds/models.py

from django.db import models
from django.core.files.base import ContentFile
from projects.models import FlutterProject
import os


class Build(models.Model):
    """Represents a Flutter build request"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('building', 'Building'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    BUILD_TYPE_CHOICES = [
        ('debug', 'Debug'),
        ('release', 'Release'),
        ('profile', 'Profile'),
    ]

    # Relationships
    project = models.ForeignKey(FlutterProject, on_delete=models.CASCADE, related_name='builds')

    # Build configuration
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    build_type = models.CharField(max_length=20, choices=BUILD_TYPE_CHOICES, default='release')

    # Version info
    version_number = models.CharField(max_length=20, default='1.0.0')
    build_number = models.IntegerField(default=1)

    # Build output
    apk_file = models.FileField(upload_to='apks/', null=True, blank=True)
    apk_size = models.BigIntegerField(null=True, blank=True)  # Size in bytes

    # Build environment
    flutter_version = models.CharField(max_length=50, blank=True)
    dart_version = models.CharField(max_length=50, blank=True)

    # Error tracking
    error_message = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Duration in seconds
    duration_seconds = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.project.name} - Build #{self.id}"

    def save_apk(self, apk_path: str):
        """Save APK file to storage"""
        if os.path.exists(apk_path):
            with open(apk_path, 'rb') as f:
                filename = f"{self.project.package_name}-{self.version_number}-{self.build_type}.apk"
                self.apk_file.save(filename, ContentFile(f.read()))
                self.apk_size = os.path.getsize(apk_path)
                self.save()


class BuildLog(models.Model):
    """Stores build process logs"""

    LEVEL_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]

    build = models.ForeignKey(Build, on_delete=models.CASCADE, related_name='logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='info')
    stage = models.CharField(max_length=50)  # e.g., 'setup', 'compile', 'package'
    message = models.TextField()

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"[{self.level}] {self.stage}: {self.message[:50]}..."