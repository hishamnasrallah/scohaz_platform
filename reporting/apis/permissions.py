from rest_framework.permissions import BasePermission
from django.db.models import Q
from reporting.models import Report, ReportSchedule, SavedReportResult


class ReportPermission(BasePermission):
    """
    Custom permission class for Report objects.
    
    Permissions:
    - List: Can see public reports and reports shared with them
    - Create: Authenticated users can create reports
    - View: Owner, shared users/groups, or public reports
    - Edit: Owner or explicitly shared with edit permission
    - Delete: Owner only (unless superuser)
    - Execute: Owner, shared users/groups, public reports, or has execute permission
    """

    def has_permission(self, request, view):
        """Check if user has permission to access reports endpoint."""
        if not request.user.is_authenticated:
            return False

        # For list and create operations
        if view.action in ['list', 'create', 'available_models', 'builder_data']:
            return True

        # For operations that don't require object permissions
        if view.action in ['metadata']:
            return True

        return True  # Object-level permissions will be checked

    def has_object_permission(self, request, view, obj):
        """Check if user has permission for a specific report."""
        user = request.user

        # Superusers have all permissions
        if user.is_superuser:
            return True

        # Read permissions
        if view.action in ['retrieve', 'preview']:
            return self._has_read_permission(user, obj)

        # Execute permissions
        if view.action in ['execute']:
            return self._has_execute_permission(user, obj)

        # Write permissions
        if view.action in ['update', 'partial_update']:
            return self._has_write_permission(user, obj)

        # Delete permissions
        if view.action == 'destroy':
            return self._has_delete_permission(user, obj)

        # Duplicate permissions (same as read)
        if view.action == 'duplicate':
            return self._has_read_permission(user, obj)

        return False

    def _has_read_permission(self, user, report):
        """Check if user can read/view the report."""
        # Public reports
        if report.is_public:
            return True

        # Owner
        if report.created_by == user:
            return True

        # Shared with user
        if report.shared_with_users.filter(id=user.id).exists():
            return True

        # Shared with user's groups
        if report.shared_with_groups.filter(id__in=user.groups.all()).exists():
            return True

        # Has specific view permission
        if user.has_perm('reporting.view_report'):
            return True

        return False

    def _has_write_permission(self, user, report):
        """Check if user can edit the report."""
        # Owner
        if report.created_by == user:
            return True

        # Has specific change permission
        if user.has_perm('reporting.change_report'):
            return True

        # Could extend to check if shared with write permission
        # For now, only owner can edit
        return False

    def _has_delete_permission(self, user, report):
        """Check if user can delete the report."""
        # Only owner can delete
        if report.created_by == user:
            return True

        # Has specific delete permission
        if user.has_perm('reporting.delete_report'):
            return True

        return False

    def _has_execute_permission(self, user, report):
        """Check if user can execute the report."""
        # If user can read, they can execute
        if self._has_read_permission(user, report):
            return True

        # Has specific execute permission
        if user.has_perm('reporting.execute_report'):
            return True

        return False


class ReportComponentPermission(BasePermission):
    """
    Permission class for report components (fields, filters, etc.).
    
    Users can only modify components of reports they own.
    """

    def has_permission(self, request, view):
        """Check general permission."""
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Check object-level permission."""
        user = request.user

        # Superusers have all permissions
        if user.is_superuser:
            return True

        # Get the report associated with this component
        report = obj.report

        # Only report owner can modify components
        if view.action in ['create', 'update', 'partial_update', 'destroy']:
            return report.created_by == user

        # For read operations, use report read permissions
        return ReportPermission()._has_read_permission(user, report)


class ReportSchedulePermission(BasePermission):
    """
    Permission class for report schedules.
    
    Users can only manage schedules for reports they have execute permission on.
    """

    def has_permission(self, request, view):
        """Check general permission."""
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Check object-level permission."""
        user = request.user

        # Superusers have all permissions
        if user.is_superuser:
            return True

        # Schedule creator can manage their schedules
        if obj.created_by == user:
            return True

        # Report owner can manage schedules for their reports
        if obj.report.created_by == user:
            return True

        return False


class SavedResultPermission(BasePermission):
    """
    Permission class for saved report results.
    
    Similar to reports - owner, shared users/groups, or public.
    """

    def has_permission(self, request, view):
        """Check general permission."""
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Check object-level permission."""
        user = request.user

        # Superusers have all permissions
        if user.is_superuser:
            return True

        # Read permissions
        if view.action in ['retrieve', 'download']:
            return self._has_read_permission(user, obj)

        # Write permissions
        if view.action in ['update', 'partial_update']:
            return obj.saved_by == user

        # Delete permissions
        if view.action == 'destroy':
            return obj.saved_by == user

        return False

    def _has_read_permission(self, user, saved_result):
        """Check if user can read the saved result."""
        # Public results
        if saved_result.is_public:
            return True

        # Owner
        if saved_result.saved_by == user:
            return True

        # Shared with user
        if saved_result.shared_with_users.filter(id=user.id).exists():
            return True

        # Shared with user's groups
        if saved_result.shared_with_groups.filter(id__in=user.groups.all()).exists():
            return True

        return False


# Row-level security mixin
class ReportSecurityMixin:
    """
    Mixin to add row-level security to report queries.
    
    Can be used to filter report data based on user permissions.
    """

    def apply_row_level_security(self, queryset, user, report):
        """
        Apply row-level security filters to a queryset.
        
        Override this method in specific implementations.
        
        Args:
            queryset: The base queryset
            user: The user executing the report
            report: The report being executed
            
        Returns:
            Filtered queryset
        """
        # Example implementation - filter by user's organization
        # if hasattr(queryset.model, 'organization') and hasattr(user, 'organization'):
        #     queryset = queryset.filter(organization=user.organization)

        # Example - filter by user's assigned records
        # if hasattr(queryset.model, 'assigned_to'):
        #     queryset = queryset.filter(
        #         Q(assigned_to=user) |
        #         Q(created_by=user) |
        #         Q(is_public=True)
        #     )

        return queryset

    def get_user_data_filters(self, user, model):
        """
        Get filters that should be applied for a user on a model.
        
        Returns a Q object or None.
        """
        filters = Q()

        # Add custom filter logic here based on your requirements
        # Example: User can only see their department's data
        # if hasattr(model, 'department') and hasattr(user, 'department'):
        #     filters &= Q(department=user.department)

        return filters if filters else None


# Utility functions for permission checking

def user_can_execute_report(user, report):
    """Check if a user can execute a specific report."""
    permission = ReportPermission()
    return permission._has_execute_permission(user, report)


def user_can_edit_report(user, report):
    """Check if a user can edit a specific report."""
    permission = ReportPermission()
    return permission._has_write_permission(user, report)


def user_can_delete_report(user, report):
    """Check if a user can delete a specific report."""
    permission = ReportPermission()
    return permission._has_delete_permission(user, report)


def get_reports_for_user(user):
    """Get all reports accessible to a user."""
    if user.is_superuser:
        return Report.objects.all()

    return Report.objects.filter(
        Q(created_by=user) |
        Q(shared_with_users=user) |
        Q(shared_with_groups__in=user.groups.all()) |
        Q(is_public=True)
    ).distinct()


# Permission decorators

from functools import wraps
from django.core.exceptions import PermissionDenied


def require_report_permission(permission_type='read'):
    """
    Decorator to check report permissions.
    
    Usage:
        @require_report_permission('execute')
        def my_view(request, report_id):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, report_id, *args, **kwargs):
            try:
                report = Report.objects.get(id=report_id)
            except Report.DoesNotExist:
                raise PermissionDenied("Report not found")

            permission = ReportPermission()

            if permission_type == 'read':
                has_perm = permission._has_read_permission(request.user, report)
            elif permission_type == 'write':
                has_perm = permission._has_write_permission(request.user, report)
            elif permission_type == 'delete':
                has_perm = permission._has_delete_permission(request.user, report)
            elif permission_type == 'execute':
                has_perm = permission._has_execute_permission(request.user, report)
            else:
                has_perm = False

            if not has_perm:
                raise PermissionDenied(f"You don't have {permission_type} permission for this report")

            return func(request, report_id, *args, **kwargs)
        return wrapper
    return decorator