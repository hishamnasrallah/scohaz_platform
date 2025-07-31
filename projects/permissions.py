from rest_framework import permissions


class IsProjectOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of a project to access it.
    """

    def has_object_permission(self, request, view, obj):
        # Check if the object has a project attribute (for Screen, Build models)
        if hasattr(obj, 'project'):
            return obj.project.user == request.user

        # Check if the object is a FlutterProject
        if hasattr(obj, 'user'):
            return obj.user == request.user

        return False


class IsProjectOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of a project to edit it.
    Read permissions are allowed to any authenticated user.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner
        if hasattr(obj, 'project'):
            return obj.project.user == request.user

        if hasattr(obj, 'user'):
            return obj.user == request.user

        return False


class CanTriggerBuild(permissions.BasePermission):
    """
    Permission to check if user can trigger a build for a project.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user.is_authenticated:
            return False

        # Check if project_id is in request data
        project_id = request.data.get('project_id')
        if not project_id:
            return True  # Let serializer validation handle this

        # Check if user owns the project
        from projects.models import FlutterProject
        return FlutterProject.objects.filter(
            id=project_id,
            user=request.user
        ).exists()


class IsStaffOrReadOnly(permissions.BasePermission):
    """
    Permission class for admin-managed models like ComponentTemplate.
    Staff can edit, others can only read.
    """

    def has_permission(self, request, view):
        # Read permissions for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated

        # Write permissions only for staff
        return request.user.is_staff