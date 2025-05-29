from django.shortcuts import render, get_object_or_404
from .models import Repository

def repository_list(request):
    """
    Display a list of all active (non-deleted) repositories.
    """
    repositories = Repository.active.all()
    return render(request, 'version_control/repository_list.html', {'repositories': repositories})

def repository_detail(request, pk):
    """
    Display details and commit history for a single repository.
    """
    repository = get_object_or_404(Repository, pk=pk, is_deleted=False)
    return render(request, 'version_control/repository_detail.html', {'repository': repository})
