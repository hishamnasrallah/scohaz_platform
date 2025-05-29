from django.db import models
from authentication.models import CustomUser


# Custom manager to filter only active (non-deleted) repositories.
class ActiveRepositoryManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

class Repository(models.Model):
    SCOPE_CHOICES = [
        ('project', 'Per Project'),
        ('user', 'Per User'),
        ('shared', 'Shared'),
    ]
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES)
    owner = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)  # Soft deletion flag

    # Managers: default and one that filters out deleted repositories.
    objects = models.Manager()
    active = ActiveRepositoryManager()

    def delete(self, *args, **kwargs):
        """
        Override the delete method to perform a soft delete.
        Instead of removing the record, mark it as deleted.
        """
        self.is_deleted = True
        self.save()

    def restore(self):
        """
        Restore a soft-deleted repository.
        """
        self.is_deleted = False
        self.save()

    def __str__(self):
        return self.name

class Branch(models.Model):
    repository = models.ForeignKey(Repository, related_name="branches", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    head = models.ForeignKey(
        'Commit',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='branch_head_set'  # Custom related name to avoid conflicts
    )

    def __str__(self):
        return f"{self.repository.name}:{self.name}"


class Commit(models.Model):
    repository = models.ForeignKey(Repository, related_name="commits", on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, related_name="commits", on_delete=models.CASCADE)
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Commit {self.id} on {self.repository.name} at {self.timestamp}"

class FileVersion(models.Model):
    commit = models.ForeignKey(Commit, related_name="file_versions", on_delete=models.CASCADE)
    file_path = models.CharField(max_length=500)
    full_content = models.TextField(blank=True)   # Full snapshot of the file
    diff_content = models.TextField(blank=True)     # Diff from previous version
    is_snapshot = models.BooleanField(default=True) # True if storing a full snapshot

    def __str__(self):
        return f"{self.file_path} @ commit {self.commit.id}"
