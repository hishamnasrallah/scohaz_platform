from django.contrib import admin

from case.models import Note
# from conditional_approval.forms import ApprovalStepConditionInlineForm
from conditional_approval.models import (ApprovalStep, Action,
                                         ActionStep, ApprovalStepCondition, ParallelApprovalGroup)


@admin.register(Action)
class BeneficiaryTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'name_ara', 'code', 'active_ind']


class ActionStepInline(admin.TabularInline):  # or admin.StackedInline
    model = ActionStep
    extra = 1  # Number of empty forms to display
    fields = ('id', 'approval_step', 'action',
              'to_status', 'sub_status', 'active_ind')
    readonly_fields = ()  # Add any fields that should not be editable here if needed
    # fk_name = 'approval_step'  # Specify the ForeignKey to use


class ApprovalStepConditionInline(admin.TabularInline):  # or admin.StackedInline
    model = ApprovalStepCondition
    extra = 1  # Number of empty forms to display
    # form = ApprovalStepConditionInlineForm  # Use the custom form
    fields = ('id', 'approval_step', 'type', 'condition_logic',
              'to_status', 'sub_status', 'active_ind')
    readonly_fields = ()  # Add any fields that should not be editable here if needed
    # fk_name = 'approval_step'  # Specify the ForeignKey to use

    class Media:
        # Load our custom JS file that handles dynamic field switching
        js = ('js/condition_expression_switcher.js')


@admin.register(ParallelApprovalGroup)
class ParallelApprovalGroupAdmin(admin.ModelAdmin):
    list_display = ('approval_step', 'group')
    list_filter = ('approval_step__service_type', 'group')
    search_fields = ('approval_step__service_type__name', 'group__name')
    fieldsets = (
        ('Parallel Approval Group Details', {
            'fields': ('approval_step', 'group')
        }),
    )


class ParallelApprovalGroupInline(admin.TabularInline):
    model = ParallelApprovalGroup
    extra = 1


@admin.register(ApprovalStep)
class ApprovalStepAdmin(admin.ModelAdmin):
    list_display = ('id', 'service_type', 'seq', 'step_type',
                    'status', 'group', 'required_approvals', 'active_ind')

    list_filter = ('service_type', 'step_type', 'group', 'active_ind')
    search_fields = ('service_type__name', 'service_type__name_ara',
                     'group__name', 'status__name', 'status__name_ara')
    ordering = ('service_type', 'seq',)
    list_display_links = ('id',)
    list_editable = ('service_type', 'seq', 'step_type',
                     'status', 'group', 'required_approvals', 'active_ind')

    inlines = [ActionStepInline, ApprovalStepConditionInline, ParallelApprovalGroupInline]

    fieldsets = (
        ('Approval Step Details', {
            'fields': ('service_type', 'seq', 'step_type', 'status', 'group', 'active_ind')
        }),
        ('Parallel Approval Settings', {
            'fields': ('required_approvals', 'priority_approver_groups'),
            'classes': ('collapse',)
        }),
    )

    class Media:
        js = ('js/hide_buttons.js',)

    def get_list_filter(self, request):
        return self.list_filter

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        foreign_key_fields = ['service_type']
        for field in foreign_key_fields:
            if field in form.base_fields:
                form.base_fields[field].widget.can_add_related = False
                form.base_fields[field].widget.can_change_related = False
                form.base_fields[field].widget.can_delete_related = False

        return form


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('case', 'author', 'content_preview', 'related_approval_record', 'created_at', 'created_by')
    list_filter = ('created_at', 'author', 'case', 'related_approval_record')
    search_fields = ('content', 'case__serial_number', 'author__username', 'created_by__username', 'updated_by__username')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')

    fieldsets = (
        (None, {
            'fields': ('case', 'author', 'content', 'related_approval_record')
        }),
        ('Audit Information', {
            'fields': ('created_at', 'created_by', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

    def content_preview(self, obj):
        """Show first 50 characters of note content"""
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = "Content Preview"

    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by on initial creation
            obj.created_by = request.user
        obj.updated_by = request.user  # Always set updated_by on save
        super().save_model(request, obj, form, change)