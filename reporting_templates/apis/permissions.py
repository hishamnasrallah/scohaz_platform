from rest_framework import permissions
from authentication.crud.managers import user_can


class PDFTemplatePermission(permissions.BasePermission):
    """
    Custom permission class for PDF templates using your CRUD system
    """

    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True

        model = view.get_queryset().model

        if view.action == 'create':
            return user_can(request.user, 'create', model, 'api')
        elif view.action in ['list', 'retrieve']:
            return user_can(request.user, 'read', model, 'api')
        elif view.action in ['update', 'partial_update']:
            return user_can(request.user, 'update', model, 'api')
        elif view.action == 'destroy':
            return user_can(request.user, 'delete', model, 'api')

        # For custom actions, require read permission
        return user_can(request.user, 'read', model, 'api')

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        # Check if user created the template
        if hasattr(obj, 'created_by') and obj.created_by == request.user:
            return True

        # Check group permissions
        if hasattr(obj, 'groups'):
            user_groups = request.user.groups.all()
            if obj.groups.filter(id__in=user_groups).exists():
                return True

        return False