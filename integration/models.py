# integration/models.py - Enhanced version with URL parameters

from django.db import models
from utils.integration_helper import APIRequestHelper
import re
from typing import Dict, Any


class Integration(models.Model):
    INTEGRATION_TYPES = [
        ('API', 'API'),
        ('Webhook', 'Webhook'),
        ('Database', 'Database'),
    ]

    AUTHENTICATION_TYPES = [
        ('None', 'None'),
        ('Basic', 'Basic'),
        ('Bearer', 'Bearer'),
    ]

    name = models.CharField(max_length=100)
    integration_type = models.CharField(max_length=20, choices=INTEGRATION_TYPES)

    # URL template with placeholders like {user_id}, {number}, etc.
    endpoint = models.CharField(
        max_length=255,
        help_text="API endpoint URL. Use {placeholder} for path parameters. Example: /api/users/{user_id}/"
    )

    method = models.CharField(
        max_length=10,
        choices=[('GET', 'GET'), ('POST', 'POST'), ('PUT', 'PUT'), ('DELETE', 'DELETE')]
    )
    headers = models.JSONField(default=dict, blank=True, null=True)
    request_body = models.JSONField(default=dict, blank=True, null=True)
    query_params = models.JSONField(default=dict, blank=True, null=True)
    authentication_type = models.CharField(
        max_length=20, choices=AUTHENTICATION_TYPES, default='None'
    )
    auth_credentials = models.JSONField(default=dict, blank=True, null=True)

    # New field for URL path parameter mapping
    path_param_mapping = models.JSONField(
        default=dict,
        blank=True,
        help_text="Map URL placeholders to field names. Example: {'number': 'phone_number', 'user_id': 'applicant_id'}"
    )

    active_ind = models.BooleanField(default=True)
    response_mapping = models.JSONField(default=dict, blank=True)
    max_retries = models.IntegerField(default=3)
    retry_delay = models.IntegerField(default=60)

    def __str__(self):
        return self.name

    def build_url(self, path_params: Dict[str, Any]) -> str:
        """
        Build the final URL by replacing placeholders with actual values.
        
        Example:
            endpoint: "http://localhost:8001/mock_api/user_info/{number}/"
            path_params: {"number": "1234567890"}
            returns: "http://localhost:8001/mock_api/user_info/1234567890/"
        """
        url = self.endpoint

        # Find all placeholders in the URL
        placeholders = re.findall(r'\{(\w+)\}', url)

        for placeholder in placeholders:
            if placeholder in path_params:
                value = str(path_params[placeholder])
                url = url.replace(f'{{{placeholder}}}', value)
            else:
                raise ValueError(f"Missing required path parameter: {placeholder}")

        return url

    def make_api_request(self, body=None, query_params=None, headers=None, path_params=None):
        """
        Enhanced method that handles URL path parameters.
        """
        # Build the final URL with path parameters
        if path_params:
            url = self.build_url(path_params)
        else:
            url = self.endpoint

        # Use the existing helper with the built URL
        helper = APIRequestHelper(self)
        # We need to modify the helper to accept a custom URL
        return helper.call_api(
            body=body,
            query_params=query_params,
            headers=headers,
            custom_url=url  # Pass the built URL
        )


class FieldIntegration(models.Model):
    """Enhanced FieldIntegration with path parameter support"""

    TRIGGER_EVENTS = [
        ('on_change', 'On Change'),
        ('pre_save', 'Pre Save'),
        ('post_save', 'Post Save'),
    ]

    field = models.ForeignKey(
        'dynamicflow.Field',
        on_delete=models.CASCADE,
        related_name='field_integrations'
    )
    integration = models.ForeignKey(
        'Integration',
        on_delete=models.CASCADE,
        related_name='field_integrations'
    )
    trigger_event = models.CharField(max_length=20, choices=TRIGGER_EVENTS)
    is_async = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    condition_expression = models.TextField(blank=True)

    # Request mappings
    payload_mapping = models.JSONField(default=dict, blank=True)
    query_param_mapping = models.JSONField(default=dict, blank=True)
    header_mapping = models.JSONField(default=dict, blank=True)

    # New field for URL path parameters
    path_param_mapping = models.JSONField(
        default=dict,
        blank=True,
        help_text="Override integration's path parameters. Example: {'number': 'national_id'}"
    )

    # Response handling
    update_field_on_response = models.BooleanField(default=False)
    response_field_path = models.CharField(max_length=255, blank=True)
    response_field_mapping = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['field', 'trigger_event', 'order']
        unique_together = [['field', 'integration', 'trigger_event']]

    def __str__(self):
        return f"{self.field._field_name} -> {self.integration.name} ({self.trigger_event})"


    def prepare_request_data(self, case_data, field_value):
        """
        Enhanced to also prepare path parameters.
        """
        def get_value(data, path):
            """Extract value from data using dot notation"""
            if path == 'field_value':
                return field_value

            keys = path.split('.')
            current = data
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            return current

        # Prepare payload
        payload = {}
        for api_key, case_key in self.payload_mapping.items():
            value = get_value(case_data, case_key)
            if value is not None:
                payload[api_key] = value

        # Prepare query params
        query_params = {}
        for api_key, case_key in self.query_param_mapping.items():
            value = get_value(case_data, case_key)
            if value is not None:
                query_params[api_key] = value

        # Prepare headers
        headers = {}
        for api_key, case_key in self.header_mapping.items():
            value = get_value(case_data, case_key)
            if value is not None:
                headers[api_key] = str(value)

        # NEW: Prepare path parameters
        path_param_config = self.path_param_mapping or self.integration.path_param_mapping
        path_params = {}
        for param_name, case_key in path_param_config.items():
            value = get_value(case_data, case_key)
            if value is not None:
                path_params[param_name] = value

        return payload, query_params, headers, path_params  # Now returns 4 values


# utils/integration_helper.py - Updated helper to handle custom URLs

import requests
from base64 import b64encode


class APIRequestHelper:
    def __init__(self, integration):
        self.integration = integration

    def call_api(self, body=None, query_params=None, headers=None, custom_url=None):
        """
        Make API request with support for custom URLs (with replaced path parameters).
        """
        # Use custom URL if provided, otherwise use the integration's endpoint
        url = custom_url or self.integration.endpoint

        method = self.integration.method

        # Build headers
        request_headers = {
            'Content-Type': 'application/json',
            **(self.integration.headers or {}),
            **(headers or {})
        }

        # Add authentication
        if self.integration.authentication_type == 'Basic':
            credentials = f"{self.integration.auth_credentials.get('username')}:{self.integration.auth_credentials.get('password')}"
            request_headers['Authorization'] = f'Basic {b64encode(credentials.encode()).decode()}'
        elif self.integration.authentication_type == 'Bearer':
            request_headers['Authorization'] = f"Bearer {self.integration.auth_credentials.get('token')}"

        # Merge query parameters
        final_query_params = {
            **(self.integration.query_params or {}),
            **(query_params or {})
        }

        # Merge request body
        if method in ['POST', 'PUT', 'PATCH']:
            final_body = {
                **(self.integration.request_body or {}),
                **(body or {})
            }
        else:
            final_body = None

        # Make the request
        response = requests.request(
            method=method,
            url=url,
            headers=request_headers,
            json=final_body,
            params=final_query_params
        )

        response.raise_for_status()

        # Return JSON response if available
        try:
            return response.json()
        except:
            return {'status_code': response.status_code, 'text': response.text}