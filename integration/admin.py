from django.contrib import admin
from .models import Integration, FieldIntegration
import requests
from django.contrib import messages


class FieldIntegrationInline(admin.TabularInline):
    model = FieldIntegration
    extra = 1
    fields = [
        'field', 'trigger_event', 'is_async', 'active', 'order',
        'condition_expression', 'update_field_on_response'
    ]
    autocomplete_fields = ['field']

@admin.register(FieldIntegration)
class FieldIntegrationAdmin(admin.ModelAdmin):
    list_display = [
        'field_name', 'integration_name', 'trigger_event',
        'is_async', 'active', 'order'
    ]
    list_filter = ['trigger_event', 'is_async', 'active', 'integration']
    search_fields = ['field___field_name', 'integration__name']
    autocomplete_fields = ['field', 'integration']

    fieldsets = (
        ('Basic Configuration', {
            'fields': ('field', 'integration', 'trigger_event', 'is_async', 'active', 'order')
        }),
        ('Execution Condition', {
            'fields': ('condition_expression',),
            'classes': ('collapse',)
        }),
        ('Request Mapping', {
            'fields': (
                'path_param_mapping',  # ⭐ MISSING - Add this!
                'payload_mapping',
                'query_param_mapping',
                'header_mapping'
            ),
            'classes': ('collapse',)
        }),
        ('Response Handling', {
            'fields': ('update_field_on_response', 'response_field_path', 'response_field_mapping'),
            'classes': ('collapse',)
        })
    )

    def field_name(self, obj):
        return obj.field._field_name
    field_name.short_description = 'Field'

    def integration_name(self, obj):
        return obj.integration.name
    integration_name.short_description = 'Integration'

@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ('name', 'integration_type', 'endpoint', 'method', 'active_ind')  # ⭐ Add active_ind
    search_fields = ('name',)
    list_filter = ('integration_type', 'method', 'active_ind')  # ⭐ Add active_ind

    inlines = [FieldIntegrationInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'integration_type', 'active_ind')  # ⭐ Add active_ind
        }),
        ('API Configuration', {
            'fields': (
                'endpoint',
                'method',
                'path_param_mapping',  # ⭐ MISSING - Add this!
                'headers',
                'request_body',
                'query_params'
            )
        }),
        ('Authentication', {
            'fields': ('authentication_type', 'auth_credentials'),
            'classes': ('collapse',)
        }),
        ('Response & Retry Configuration', {
            'fields': ('response_mapping', 'max_retries', 'retry_delay'),
            'classes': ('collapse',)
        })
    )

    actions = ['test_integration']

    def test_integration(self, request, queryset):
        for integration in queryset:
            try:
                # ⭐ Updated to handle path parameters
                # For testing, use sample values
                test_path_params = {}
                if integration.path_param_mapping:
                    # Use dummy values for testing
                    for param_name in integration.path_param_mapping.keys():
                        test_path_params[param_name] = "TEST_VALUE"

                response = integration.make_api_request(path_params=test_path_params)

                # Show the URL that was called
                if test_path_params:
                    test_url = integration.build_url(test_path_params)
                    messages.success(
                        request,
                        f"Tested {integration.name} at {test_url}: {response}"
                    )
                else:
                    messages.success(
                        request,
                        f"Tested {integration.name}: {response}"
                    )
            except Exception as e:
                messages.error(
                    request,
                    f"Error testing {integration.name}: {str(e)}"
                )

    test_integration.short_description = "Test selected integrations"