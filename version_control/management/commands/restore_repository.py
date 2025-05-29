from django.core.management.base import BaseCommand, CommandError
from version_control.models import Repository

class Command(BaseCommand):
    help = 'Restore a soft-deleted repository by its ID'

    def add_arguments(self, parser):
        parser.add_argument('repo_id', type=int, help='ID of the repository to restore')

    def handle(self, *args, **options):
        repo_id = options['repo_id']
        try:
            repo = Repository.objects.get(id=repo_id)
        except Repository.DoesNotExist:
            raise CommandError(f'Repository with ID {repo_id} does not exist')

        if not repo.is_deleted:
            self.stdout.write(self.style.WARNING('Repository is already active.'))
        else:
            repo.restore()
            self.stdout.write(self.style.SUCCESS(f'Repository with ID {repo_id} has been restored.'))
