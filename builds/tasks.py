"""
Celery tasks for asynchronous build processing.
"""

import logging
from datetime import timedelta

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail

from builds.models import Build, BuildLog
from builds.services.build_service import BuildService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    soft_time_limit=600,  # 10 minutes soft limit
    time_limit=900,  # 15 minutes hard limit
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={'max_retries': 3}
)
def process_build_task(self, build_id: int) -> dict:
    """
    Process a build asynchronously.

    Args:
        build_id: ID of the Build to process

    Returns:
        Dictionary with build result
    """
    logger.info(f"Starting async build task for build_id: {build_id}")

    try:
        # Get build instance
        build = Build.objects.get(id=build_id)

        # Check if build is still pending
        if build.status != 'pending':
            logger.warning(f"Build {build_id} is not pending, status: {build.status}")
            return {
                'success': False,
                'error': f'Build is not in pending state: {build.status}'
            }

        # Update task ID
        build.celery_task_id = self.request.id
        build.save()

        # Process build
        build_service = BuildService()
        completed_build = build_service.start_build(build)

        # Send notification if configured
        if completed_build.status == 'success':
            send_build_success_notification.delay(build_id)
        elif completed_build.status == 'failed':
            send_build_failure_notification.delay(build_id)

        return {
            'success': completed_build.status == 'success',
            'build_id': build_id,
            'status': completed_build.status,
            'apk_url': completed_build.apk_file.url if completed_build.apk_file else None
        }

    except SoftTimeLimitExceeded:
        logger.error(f"Build {build_id} exceeded time limit")

        # Update build status
        build = Build.objects.get(id=build_id)
        build.status = 'failed'
        build.error_message = 'Build exceeded time limit'
        build.completed_at = timezone.now()
        build.save()

        BuildLog.objects.create(
            build=build,
            level='ERROR',
            message='Build task exceeded time limit and was terminated'
        )

        raise

    except Build.DoesNotExist:
        logger.error(f"Build {build_id} not found")
        return {
            'success': False,
            'error': f'Build {build_id} not found'
        }

    except Exception as e:
        logger.exception(f"Build task failed for build_id: {build_id}")

        # Update build status on unhandled exception
        try:
            build = Build.objects.get(id=build_id)
            build.status = 'failed'
            build.error_message = f'Unexpected error: {str(e)}'
            build.completed_at = timezone.now()
            build.save()

            BuildLog.objects.create(
                build=build,
                level='ERROR',
                message=f'Build task failed with exception: {str(e)}'
            )
        except:
            pass

        raise


@shared_task
def process_build_queue():
    """
    Process pending builds from the queue.
    This task should be scheduled to run periodically.
    """
    logger.info("Processing build queue")

    # Get pending builds ordered by creation time
    pending_builds = Build.objects.filter(
        status='pending',
        celery_task_id__isnull=True
    ).order_by('created_at')[:5]  # Process up to 5 builds at a time

    processed = 0
    for build in pending_builds:
        # Check if we have capacity
        active_builds = Build.objects.filter(status='building').count()
        max_concurrent = getattr(settings, 'MAX_CONCURRENT_BUILDS', 3)

        if active_builds >= max_concurrent:
            logger.info(f"Max concurrent builds reached ({max_concurrent})")
            break

        # Queue the build
        try:
            process_build_task.delay(build.id)
            processed += 1
            logger.info(f"Queued build {build.id} for processing")
        except Exception as e:
            logger.error(f"Failed to queue build {build.id}: {e}")

    logger.info(f"Processed {processed} builds from queue")
    return processed


@shared_task
def cleanup_old_builds():
    """
    Clean up old build records and files.
    This task should be scheduled to run daily.
    """
    logger.info("Starting build cleanup task")

    # Get cutoff date (keep builds for 30 days by default)
    retention_days = getattr(settings, 'BUILD_RETENTION_DAYS', 30)
    cutoff_date = timezone.now() - timedelta(days=retention_days)

    # Find old builds
    old_builds = Build.objects.filter(
        created_at__lt=cutoff_date
    ).exclude(
        status__in=['pending', 'building']  # Don't delete active builds
    )

    deleted_count = 0
    for build in old_builds:
        try:
            # Delete APK file if exists
            if build.apk_file:
                build.apk_file.delete(save=False)

            # Delete build record (logs will cascade delete)
            build.delete()
            deleted_count += 1

        except Exception as e:
            logger.error(f"Failed to delete build {build.id}: {e}")

    logger.info(f"Cleaned up {deleted_count} old builds")
    return deleted_count


@shared_task
def check_stale_builds():
    """
    Check for builds that are stuck in 'building' state.
    This task should be scheduled to run every hour.
    """
    logger.info("Checking for stale builds")

    # Builds that have been building for more than 1 hour
    stale_threshold = timezone.now() - timedelta(hours=1)

    stale_builds = Build.objects.filter(
        status='building',
        started_at__lt=stale_threshold
    )

    failed_count = 0
    for build in stale_builds:
        logger.warning(f"Found stale build: {build.id}")

        # Mark as failed
        build.status = 'failed'
        build.error_message = 'Build process appears to be stuck'
        build.completed_at = timezone.now()
        build.save()

        BuildLog.objects.create(
            build=build,
            level='ERROR',
            message='Build marked as failed due to timeout (stuck in building state)'
        )

        failed_count += 1

    if failed_count > 0:
        logger.info(f"Marked {failed_count} stale builds as failed")

    return failed_count


@shared_task
def send_build_success_notification(build_id: int):
    """Send notification when build succeeds."""
    try:
        build = Build.objects.get(id=build_id)

        # Check if notifications are enabled
        if not getattr(settings, 'SEND_BUILD_NOTIFICATIONS', False):
            return

        # Get user email
        user_email = build.project.user.email
        if not user_email:
            return

        subject = f'Build Successful: {build.project.name} v{build.version}'
        message = f"""
Your Flutter app build has completed successfully!

Project: {build.project.name}
Version: {build.version}
Build Type: {build.build_type}

You can download your APK from:
{settings.SITE_URL}/api/builds/{build.id}/download/

Build Details:
- Started: {build.started_at}
- Completed: {build.completed_at}
- APK Size: {build.apk_size / 1024 / 1024:.1f} MB

Thank you for using Flutter Visual Builder!
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=True
        )

    except Exception as e:
        logger.error(f"Failed to send success notification for build {build_id}: {e}")


@shared_task
def send_build_failure_notification(build_id: int):
    """Send notification when build fails."""
    try:
        build = Build.objects.get(id=build_id)

        # Check if notifications are enabled
        if not getattr(settings, 'SEND_BUILD_NOTIFICATIONS', False):
            return

        # Get user email
        user_email = build.project.user.email
        if not user_email:
            return

        subject = f'Build Failed: {build.project.name} v{build.version}'
        message = f"""
Unfortunately, your Flutter app build has failed.

Project: {build.project.name}
Version: {build.version}
Build Type: {build.build_type}

Error: {build.error_message or 'Unknown error'}

Build Details:
- Started: {build.started_at}
- Failed: {build.completed_at}

You can view the full build logs and retry the build at:
{settings.SITE_URL}/projects/{build.project.id}/builds/{build.id}/

If you continue to experience issues, please contact support.
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=True
        )

    except Exception as e:
        logger.error(f"Failed to send failure notification for build {build_id}: {e}")