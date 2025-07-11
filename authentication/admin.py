
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

# Register your models here.

from authentication.models import CustomUser, UserPreference, UserType, PhoneNumber, CRUDPermission


from .crud.managers import user_can  # your permission-checking function

class PermissionAwareAdmin(admin.ModelAdmin):
    """
    Base admin that overrides built-in admin permission methods
    and calls user_can(...) for create, read, update, delete.
    """
    context_name = "admin"

    def has_view_permission(self, request, obj=None):
        # If you want superusers to bypass everything, keep this check:
        if request.user.is_superuser:
            return True

        # For object-level checks, pass obj.pk. For read, do "read".
        object_id = obj.pk if obj else None
        return user_can(request.user, "read", self.model, self.context_name, object_id)

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True

        # "create" permission
        return user_can(request.user, "create", self.model, self.context_name)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        # "update" permission
        object_id = obj.pk if obj else None
        return user_can(request.user, "update", self.model, self.context_name, object_id)

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        # "delete" permission
        object_id = obj.pk if obj else None
        return user_can(request.user, "delete", self.model, self.context_name, object_id)

@admin.register(CustomUser)
class UserAdmin(DjangoUserAdmin):

    fieldsets = (
        (_('Information'), {'fields': ('first_name',
                                       'second_name',
                                       'third_name',
                                       'last_name')}),
        (_('Credentials'), {'fields': ('username',
                                       'email',
                                       'password',
                                       'user_type')}),
        (_('Activation'), {'fields': ('sms_code',
                                      'sms_time',
                                      'activated_account')}),
        (_('For System Admin'), {'fields': ('is_active',
                                            'is_staff',
                                            'is_superuser',
                                            'is_developer',
                                            'groups',
                                            'user_permissions')}),
        (_('Important dates'), {'fields': (('last_login',
                                            'date_joined'),)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'user_type', 'password1', 'password2'),
        }),
    )
    readonly_fields = ('last_login', 'date_joined', 'sms_time')

    def save_related(self, request, form, formsets, change):
        """
        Override the save_related method to
        dynamically add a group based on the user_type.
        """
        # Call the parent method to ensure related fields are saved first
        super().save_related(request, form, formsets, change)

        # Dynamic group assignment logic
        self.add_user_to_group(form)

    def add_user_to_group(self, form):
        """
        Helper function to add the user to a group based on their user_type.
        """
        user_type = form.instance.user_type
        if user_type and user_type.group:
            user_type_group = user_type.group

            # Add user to the group if not already a member
            if not form.instance.groups.filter(id=user_type_group.id).exists():
                self.assign_group(form, user_type_group)
            # No need for else statement, as we don't need to print or log anything
        else:
            # Optional: You can leave this empty, or add a comment for missing user_type
            pass

    def assign_group(self, form, group):
        """
        Helper function to assign a group to the user and save the instance.
        """
        form.instance.groups.add(group)
        form.instance.save()


@admin.register(UserPreference)
class UserPreferenceAdmin(PermissionAwareAdmin):
    """
    Custom admin interface for UserPreference.
    """
    # Fields to display in the list view
    list_display = ('user', 'lang')
    # Allow searching by user username and language
    search_fields = ('user__username', 'lang')
    list_filter = ('lang',)  # Filter by language
    ordering = ('user',)  # Default ordering by user


    def get_readonly_fields(self, request, obj=None):
        """
        Optionally make the user field readonly, since it’s a one-to-one relationship.
        """
        if obj:
            # Make the user field readonly if the object exists (i.e., when editing)
            return ('user',)
        return super().get_readonly_fields(request, obj)


@admin.register(UserType)
class UserTypeAdmin(admin.ModelAdmin):
    """
    Custom admin interface for UserType.
    """
    list_display = ('name', 'code', 'active_ind', 'group', 'permissions_count')
    search_fields = ('name', 'name_ara', 'code')
    list_filter = ('active_ind',)  # Filter by active status
    ordering = ('name',)  # Default ordering by name

    # Add custom method to show the number of permissions associated with the user type
    def permissions_count(self, obj):
        return obj.permissions.count()
    permissions_count.short_description = _('permissions count')

    def get_readonly_fields(self, request, obj=None):
        """
        Optionally make the group field readonly, since it is dynamically managed.
        """
        # if obj and obj.group:
        #     return ('group',)  # Make the group field readonly if the group exists
        return super().get_readonly_fields(request, obj)


@admin.register(PhoneNumber)
class PhoneNumberAdmin(admin.ModelAdmin):
    list_display = ['id', 'user']
    search_fields = ["user__username", "user__first_name", "phone_number"]


@admin.register(CRUDPermission)
class CRUDPermissionAdmin(admin.ModelAdmin):
    list_display = ['id', 'group__name', 'content_type__app_label', 'content_type__model']
    search_fields = ["user__username", "user__first_name", "phone_number"]

# admin.site.unregister(Group)

# @admin.register(Group)
# class GroupAdmin(admin.ModelAdmin):
#     list_display = ['name',]
#     search_fields = ['name']
#
#     admin_group = "authentication"
