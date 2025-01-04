
from django.utils.deprecation import MiddlewareMixin
from crm.models import IntegrationConfig

class DynamicModelMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Add logic to handle requests dynamically
        if request.path.startswith('/crm/'):
            print(f"Processing request for crm: {request.path}")

    def process_response(self, request, response):
        # Add logic to handle responses dynamically
        if request.path.startswith('/crm/'):
            print(f"Processing response for crm: {response.status_code}")
        return response
