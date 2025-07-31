"""
Management command to clean up old builds and temporary files.
"""

import os
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from django.db.models import Q

from builds.models import Build, BuildLog
from builds.utils.file_manager import FileManager


class Command(BaseCommand):
    help = 'Clean up old builds and temporary files'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file_manager = FileManager()

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to keep builds (default: 30)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
        parser.add_argument(
            '--keep-failed',
            action='store_true',
            help='Keep failed builds for debugging'
        )
        parser.add_argument(
            '--clean-temp',
            action='store_true',
            help='Clean temporary build directories'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force cleanup without confirmation'
        )

    def handle(self, *args, **options):
        retention_days = options['days']
        dry_run = options['dry_run']
        keep_failed = options['keep_failed']
        clean_temp = options['clean_temp']
        force = options['force']

        self.stdout.write(
            self.style.SUCCESS(
                f'Cleaning up builds older than {retention_days} days...\n'
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No files will be deleted\n')
            )

        # Clean old builds
        deleted_builds = self.clean_old_builds(
            retention_days, dry_run, keep_failed
        )

        # Clean orphaned files
        orphaned_files = self.clean_orphaned_files(dry_run)

        # Clean temporary directories
        if clean_temp:
            temp_cleaned = self.clean_temp_directories(dry_run)
        else:
            temp_cleaned = 0

        # Summary
        self.stdout.write('\n' + self.style.SUCCESS('Cleanup Summary:'))
        self.stdout.write(f'  Builds deleted: {deleted_builds}')
        self.stdout.write(f'  Orphaned files: {orphaned_files}')
        if clean_temp:
            self.stdout.write(f'  Temp directories: {temp_cleaned}')

        if not dry_run and (deleted_builds > 0 or orphaned_files > 0):
            self.stdout.write(
                self.style.SUCCESS('\nCleanup completed successfully!')
            )

    def clean_old_builds(self, retention_days, dry_run, keep_failed):
        """Clean builds older than retention period."""
        cutoff_date = timezone.now() - timedelta(days=retention_days)

        # Find old builds
        old_builds = Build.objects.filter(
            created_at__lt=cutoff_date
        ).exclude(
            status__in=['pending', 'building']  # Don't delete active builds
        )

        if keep_failed:
            old_builds = old_builds.exclude(status='failed')

        self.stdout.write(f'Found {old_builds.count()} builds to delete')

        deleted_count = 0
        total_size = 0

        for build in old_builds:
            # Calculate size
            if build.apk_file:
                try:
                    size = build.apk_file.size
                    total_size += size
                except:
                    pass

            if dry_run:
                self.stdout.write(
                    f'  Would delete: Build #{build.id} - {build.project.name} '
                    f'v{build.version} ({build.created_at.date()})'
                )
            else:
                try:
                    # Delete APK file
                    if build.apk_file:
                        build.apk_file.delete(save=False)

                    # Delete build record (logs cascade)
                    build.delete()
                    deleted_count += 1

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  Failed to delete build {build.id}: {e}')
                    )

        if not dry_run and deleted_count > 0:
            size_mb = total_size / (1024 * 1024)
            self.stdout.write(
                f'  Freed {size_mb:.1f} MB of disk space'
            )

        return deleted_count

    def clean_orphaned_files(self, dry_run):
        """Clean APK files without corresponding build records."""
        builds_dir = os.path.join(settings.MEDIA_ROOT, 'builds')
        if not os.path.exists(builds_dir):
            return 0

        orphaned_count = 0

        # Get all APK files
        apk_files = self.file_manager.find_files(builds_dir, '*.apk')

        for apk_path in apk_files:
            # Check if build exists for this file
            filename = os.path.basename(apk_path)
            relative_path = os.path.relpath(apk_path, settings.MEDIA_ROOT)

            build_exists = Build.objects.filter(
                apk_file=relative_path
            ).exists()

            if not build_exists:
                if dry_run:
                    self.stdout.write(
                        f'  Would delete orphaned file: {filename}'
                    )
                else:
                    try:
                        os.remove(apk_path)
                        orphaned_count += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f'  Failed to delete {filename}: {e}'
                            )
                        )

        return orphaned_count

    def clean_temp_directories(self, dry_run):
        """Clean temporary build directories."""
        temp_dir = getattr(settings, 'BUILD_TEMP_DIR', '/tmp')
        cleaned_count = 0

        # Look for build directories
        if os.path.exists(temp_dir):
            for item in os.listdir(temp_dir):
                if item.startswith('flutter_build_') or item.startswith('build_'):
                    dir_path = os.path.join(temp_dir, item)

                    if os.path.isdir(dir_path):
                        # Check age
                        try:
                            mtime = os.path.getmtime(dir_path)
                            age_hours = (timezone.now().timestamp() - mtime) / 3600

                            # Clean if older than 24 hours
                            if age_hours > 24:
                                if dry_run:
                                    self.stdout.write(
                                        f'  Would delete temp dir: {item} '
                                        f'({age_hours:.1f} hours old)'
                                    )
                                else:
                                    if self.file_manager.cleanup_directory(dir_path):
                                        cleaned_count += 1
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(
                                    f'  Error checking {item}: {e}'
                                )
                            )

        return cleaned_count