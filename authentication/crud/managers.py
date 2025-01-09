# authentication/crud/managers.py

from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from authentication.models import CRUDPermission

def user_can(user, action, model_class, context, object_id=None):
    """
    :param user: the user instance
    :param action: one of "create", "read", "update", "delete"
    :param model_class: e.g. BlogPost
    :param context: e.g. "api", "admin", "form_view"
    :param object_id: optional if you are checking at object level
    :return: True/False
    """
    if not user.is_authenticated:
        return False

    # We get all groups for the user
    groups = user.groups.all()  # many-to-many

    # Then for each group, we see if there's a matching permission
    content_type = ContentType.objects.get_for_model(model_class)

    # Optional: handle object-level permissions if needed
    # If object_id is set, you look for CRUDPermission with matching object_id
    # Otherwise, you look for CRUDPermission without object_id
    query = CRUDPermission.objects.filter(
        group__in=groups,
        content_type=content_type,
        context=context,
    )

    if object_id:
        query = query.filter(Q(object_id=object_id) | Q(object_id__isnull=True))
    else:
        query = query.filter(object_id__isnull=True)

    # If no record found, user doesn't have permission
    if not query.exists():
        return False

    # If found, check the boolean for create/read/update/delete
    for perm in query:
        if action == "create" and perm.can_create:
            return True
        elif action == "read" and perm.can_read:
            return True
        elif action == "update" and perm.can_update:
            return True
        elif action == "delete" and perm.can_delete:
            return True

    return False
