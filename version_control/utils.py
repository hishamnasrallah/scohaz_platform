import difflib
from django.utils import timezone
from .models import Commit, FileVersion, Branch

def generate_diff(old_text, new_text):
    """
    Generate a unified diff between two versions of text.
    """
    diff_lines = difflib.unified_diff(
        old_text.splitlines(),
        new_text.splitlines(),
        fromfile='old_version',
        tofile='new_version',
        lineterm=''
    )
    return "\n".join(diff_lines)

def create_commit(repository, branch, user, message, changed_files):
    """
    Create a new commit in the given branch.

    Parameters:
      repository: The Repository instance.
      branch: The Branch instance where the commit is added.
      user: The User making the commit.
      message: Commit message describing the change.
      changed_files: A dictionary mapping file paths to their new content.

    Process:
      - Links to the previous commit.
      - Stores a full snapshot of each changed file.
      - Generates and stores diffs compared to previous versions (if available).
      - Updates the branch head.

    Returns the new Commit instance.
    """
    parent_commit = branch.head  # Get the current latest commit in this branch
    new_commit = Commit.objects.create(
        repository=repository,
        branch=branch,
        author=user,
        message=message,
        parent=parent_commit,
        timestamp=timezone.now(),
    )

    for file_path, new_content in changed_files.items():
        full_snapshot = new_content
        previous_version = None
        if parent_commit:
            previous_version = parent_commit.file_versions.filter(file_path=file_path).last()

        if previous_version and previous_version.full_content:
            diff_result = generate_diff(previous_version.full_content, new_content)
            is_snapshot = False  # Mark as diff-based entry if a previous version exists
        else:
            diff_result = ""
            is_snapshot = True

        FileVersion.objects.create(
            commit=new_commit,
            file_path=file_path,
            full_content=full_snapshot,
            diff_content=diff_result,
            is_snapshot=is_snapshot
        )

    branch.head = new_commit  # Update branch head to the new commit
    branch.save()

    return new_commit

def create_branch(repository, name, from_commit=None):
    """
    Create a new branch for the repository.

    Parameters:
      repository: The Repository instance.
      name: The name of the branch.
      from_commit: (Optional) The commit from which the branch should start.

    Returns the new Branch instance.
    """
    branch = Branch.objects.create(
        repository=repository,
        name=name,
        head=from_commit
    )
    return branch

def fast_forward_merge(target_branch, source_branch):
    """
    Perform a fast-forward merge from source_branch into target_branch.

    This merge is only possible if target_branch is an ancestor of source_branch.
    """
    commit = source_branch.head
    while commit:
        if commit == target_branch.head:
            target_branch.head = source_branch.head
            target_branch.save()
            return target_branch
        commit = commit.parent
    raise ValueError("Fast-forward merge is not possible; branches have diverged.")

def rollback_branch(branch, target_commit):
    """
    Roll back the branch to a specified commit.

    This sets the branch head to the target commit if it exists in the branch history.
    """
    current = branch.head
    valid = False
    while current:
        if current == target_commit:
            valid = True
            break
        current = current.parent
    if not valid:
        raise ValueError("The target commit is not in this branch's history.")

    branch.head = target_commit
    branch.save()
    return branch
