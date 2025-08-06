# File: builds/tasks.py

from celery import shared_task
from celery.utils.log import get_task_logger
from builds.models import Build
from builds.services.build_service import BuildService

logger = get_task_logger(__name__)


@shared_task
def process_build_task(build_id: int):
    """Process a build asynchronously"""
    logger.info(f"Starting build task for build_id: {build_id}")

    try:
        build = Build.objects.get(id=build_id)
        logger.info(f"Processing build for project: {build.project.name}")

        service = BuildService()
        service.start_build(build)

        logger.info(f"Build {build_id} completed with status: {build.status}")

    except Build.DoesNotExist:
        logger.error(f"Build {build_id} not found")
    except Exception as e:
        logger.error(f"Error processing build {build_id}: {str(e)}", exc_info=True)


@shared_task
def cleanup_old_builds():
    """Clean up old build files to save storage space"""
    from datetime import timedelta
    from django.utils import timezone

    # Delete builds older than 30 days
    cutoff_date = timezone.now() - timedelta(days=30)
    old_builds = Build.objects.filter(created_at__lt=cutoff_date)

    count = 0
    for build in old_builds:
        if build.apk_file:
            try:
                build.apk_file.delete()
                count += 1
            except Exception as e:
                logger.error(f"Error deleting APK for build {build.id}: {e}")

    logger.info(f"Cleaned up {count} old APK files")
    return count


@shared_task
def check_build_health():
    """Check for stuck builds and mark them as failed"""
    from datetime import timedelta
    from django.utils import timezone

    # Check for builds that have been building for more than 30 minutes
    timeout = timezone.now() - timedelta(minutes=30)
    stuck_builds = Build.objects.filter(
        status='building',
        started_at__lt=timeout
    )

    count = 0
    for build in stuck_builds:
        build.status = 'failed'
        build.error_message = 'Build timeout - process may have been interrupted'
        build.completed_at = timezone.now()
        build.save()

        logger.warning(f"Marked build {build.id} as failed due to timeout")
        count += 1

    if count > 0:
        logger.info(f"Marked {count} stuck builds as failed")

    return count