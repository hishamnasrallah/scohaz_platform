from django.contrib import admin
from django.utils.html import format_html
from django.http import HttpResponse
import json
import csv
from datetime import datetime


class TimestampMixin:
    """Mixin to add timestamp fields to admin"""

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        timestamp_fields = ['created_at', 'updated_at']

        # Add timestamp fields if they exist on the model
        for field in timestamp_fields:
            if hasattr(self.model, field) and field not in readonly_fields:
                readonly_fields.append(field)

        return readonly_fields

    def created_date(self, obj):
        """Formatted created date"""
        if hasattr(obj, 'created_at') and obj.created_at:
            return obj.created_at.strftime('%Y-%m-%d %H:%M')
        return '-'
    created_date.short_description = 'Created'
    created_date.admin_order_field = 'created_at'

    def updated_date(self, obj):
        """Formatted updated date"""
        if hasattr(obj, 'updated_at') and obj.updated_at:
            return obj.updated_at.strftime('%Y-%m-%d %H:%M')
        return '-'
    updated_date.short_description = 'Updated'
    updated_date.admin_order_field = 'updated_at'


class StatusColorMixin:
    """Mixin to add colored status display"""

    STATUS_COLORS = {
        'pending': {'color': '#FFA500', 'bg': '#FFF3CD', 'label': 'Pending'},
        'building': {'color': '#0D6EFD', 'bg': '#D1E7FF', 'label': 'Building'},
        'success': {'color': '#198754', 'bg': '#D1F2EB', 'label': 'Success'},
        'failed': {'color': '#DC3545', 'bg': '#F8D7DA', 'label': 'Failed'},
        'cancelled': {'color': '#6C757D', 'bg': '#E2E3E5', 'label': 'Cancelled'},
        'active': {'color': '#198754', 'bg': '#D1F2EB', 'label': 'Active'},
        'inactive': {'color': '#6C757D', 'bg': '#E2E3E5', 'label': 'Inactive'},
    }

    def get_status_info(self, status):
        """Get status color and label"""
        info = self.STATUS_COLORS.get(
            status.lower(),
            {'color': '#000', 'bg': '#FFF', 'label': status.title()}
        )
        # Add CSS class based on status
        info['class'] = status.lower()
        return info

    def colored_status(self, obj):
        """Display status with color"""
        status = getattr(obj, 'status', None)
        if not status:
            return '-'

        info = self.get_status_info(status)
        return format_html(
            '<span style="padding: 3px 8px; border-radius: 3px; '
            'background-color: {}; color: {};">{}</span>',
            info['bg'], info['color'], info['label']
        )
    colored_status.short_description = 'Status'
    colored_status.admin_order_field = 'status'


class ExportMixin:
    """Mixin to add export functionality"""

    export_fields = None  # Override in subclass to specify fields

    def get_export_fields(self):
        """Get fields to export"""
        if self.export_fields:
            return self.export_fields

        # Default to list_display fields
        return [
            field for field in self.list_display
            if not callable(getattr(self, field, None)) and field != 'action_checkbox'
        ]

    def export_as_csv(self, request, queryset):
        """Export selected items as CSV"""
        meta = self.model._meta
        field_names = self.get_export_fields()

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={meta.verbose_name_plural}.csv'

        writer = csv.writer(response)

        # Write header
        header = []
        for field in field_names:
            if hasattr(self.model, field):
                header.append(
                    self.model._meta.get_field(field).verbose_name.title()
                )
            else:
                header.append(field.replace('_', ' ').title())
        writer.writerow(header)

        # Write data
        for obj in queryset:
            row = []
            for field in field_names:
                value = getattr(obj, field, '')

                # Handle foreign keys
                if hasattr(value, '__str__'):
                    value = str(value)

                # Handle datetime
                if isinstance(value, datetime):
                    value = value.strftime('%Y-%m-%d %H:%M:%S')

                row.append(value)
            writer.writerow(row)

        return response

    export_as_csv.short_description = 'Export selected as CSV'

    def export_as_json(self, request, queryset):
        """Export selected items as JSON"""
        meta = self.model._meta
        data = []

        for obj in queryset:
            obj_data = {}
            for field in self.get_export_fields():
                value = getattr(obj, field, None)

                # Handle foreign keys
                if hasattr(value, 'pk'):
                    value = {'id': value.pk, 'str': str(value)}

                # Handle datetime
                if isinstance(value, datetime):
                    value = value.isoformat()

                obj_data[field] = value

            data.append(obj_data)

        response = HttpResponse(
            json.dumps(data, indent=2, ensure_ascii=False),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename={meta.verbose_name_plural}.json'

        return response

    export_as_json.short_description = 'Export selected as JSON'

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions['export_as_csv'] = (
            self.export_as_csv,
            'export_as_csv',
            'Export selected as CSV'
        )
        actions['export_as_json'] = (
            self.export_as_json,
            'export_as_json',
            'Export selected as JSON'
        )
        return actions


class JSONFieldMixin:
    """Mixin for handling JSON fields in admin"""

    def pretty_json(self, obj, field_name):
        """Display pretty-printed JSON"""
        value = getattr(obj, field_name, None)
        if not value:
            return '-'

        try:
            if isinstance(value, str):
                value = json.loads(value)

            formatted = json.dumps(value, indent=2, ensure_ascii=False)

            # Truncate if too long
            if len(formatted) > 500:
                formatted = formatted[:500] + '...'

            return format_html(
                '<pre class="json-preview">{}</pre>',
                formatted
            )
        except (json.JSONDecodeError, TypeError):
            return format_html('<code>{}</code>', str(value)[:100])


class BulkActionsMixin:
    """Mixin for common bulk actions"""

    def bulk_activate(self, request, queryset):
        """Activate selected items"""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} {self.model._meta.verbose_name_plural} activated.'
        )
    bulk_activate.short_description = 'Activate selected items'

    def bulk_deactivate(self, request, queryset):
        """Deactivate selected items"""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} {self.model._meta.verbose_name_plural} deactivated.',
            level='warning'
        )
    bulk_deactivate.short_description = 'Deactivate selected items'

    def get_actions(self, request):
        actions = super().get_actions(request)

        # Add bulk actions if model has is_active field
        if hasattr(self.model, 'is_active'):
            actions['bulk_activate'] = (
                self.bulk_activate,
                'bulk_activate',
                'Activate selected items'
            )
            actions['bulk_deactivate'] = (
                self.bulk_deactivate,
                'bulk_deactivate',
                'Deactivate selected items'
            )

        return actions


class AdminStatsMixin:
    """Mixin to display statistics in admin"""

    def get_stats(self, request):
        """Override to return custom statistics"""
        return {}

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        # Add statistics to context
        stats = self.get_stats(request)
        if stats:
            extra_context['stats'] = stats

        return super().changelist_view(request, extra_context=extra_context)


class ReadOnlyMixin:
    """Mixin to make admin interface read-only"""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False