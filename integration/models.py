from django.db import models
from utils.integration_helper import APIRequestHelper


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
    integration_type = models.CharField(
        max_length=20, choices=INTEGRATION_TYPES)
    endpoint = models.CharField(
        max_length=255)  # API endpoint
    method = models.CharField(
        max_length=10, choices=[('GET', 'GET'), ('POST', 'POST'),
                                ('PUT', 'PUT'), ('DELETE', 'DELETE')])  # HTTP method
    headers = models.JSONField(
        default=dict, blank=True, null=True)  # Store custom headers
    request_body = models.JSONField(
        default=dict, blank=True, null=True)  # Store request body
    query_params = models.JSONField(
        default=dict, blank=True, null=True)  # Store query parameters
    authentication_type = models.CharField(
        max_length=20, choices=AUTHENTICATION_TYPES, default='None')  # Auth type
    auth_credentials = models.JSONField(
        default=dict, blank=True, null=True)  # Auth credentials

    def __str__(self):
        return self.name

    def make_api_request(self, body=None, query_params=None, headers=None):
        helper = APIRequestHelper(self)
        return helper.call_api(
            body=body, query_params=query_params, headers=headers)
