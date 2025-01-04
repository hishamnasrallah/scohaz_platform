from django.contrib import admin
from .models import Integration
import requests
from django.contrib import messages


@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ('name', 'integration_type', 'endpoint', 'method')
    search_fields = ('name',)

    actions = ['test_integration']

    def test_integration(self, request, queryset):
        for integration in queryset:
            try:
                response = self.make_api_request(integration)
                messages.success(request, f"Tested "
                                          f"{integration.name}: {response}")
            except Exception as e:
                messages.error(request, f"Error testing "
                                        f"{integration.name}: {str(e)}")

    test_integration.short_description = "Test selected integrations"

    def make_api_request(self, integration):
        url = integration.endpoint
        method = integration.method
        headers = {**{'Content-Type': 'application/json'},
                   **integration.headers}

        # Add authentication headers if needed
        if integration.authentication_type == 'Basic':
            from base64 import b64encode
            credentials = (f"{integration.auth_credentials.get('username')}"
                           f":{integration.auth_credentials.get('password')}")
            headers['Authorization'] = (f'Basic '
                                        f'{b64encode(credentials.encode()).decode()}')
        elif integration.authentication_type == 'Bearer':
            headers['Authorization'] = (f"Bearer "
                                        f"{integration.auth_credentials.get('token')}")

        # Prepare data for the request
        if method in ['POST', 'PUT']:
            data = integration.request_body
        else:
            data = None

        # Add query parameters for GET requests
        if method == 'GET':
            response = requests.get(
                url, headers=headers, params=integration.query_params)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data)
        elif method == 'PUT':
            response = requests.put(url, headers=headers, json=data)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers)

        response.raise_for_status()  # Raise an error for bad responses
        return response.json()
