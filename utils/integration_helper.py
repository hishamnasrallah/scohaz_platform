import requests
from django.conf import settings


class APIRequestHelper:
    def __init__(self, integration):
        self.integration = integration

    def call_api(self, body=None,
                 query_params=None, headers=None):
        # Set default values
        url = self.integration.endpoint
        method = self.integration.method

        # Prepare headers
        final_headers = {
            **{'Content-Type': 'application/json'},
            **self.integration.headers}
        if headers:
            final_headers.update(headers)

        # Prepare request body
        final_body = body if body is not None \
            else self.integration.request_body

        # Prepare query parameters
        final_query_params = query_params \
            if query_params is not None \
            else self.integration.query_params

        # Check if the URL is internal or external
        if url.startswith('/api/'):
            url = f"{settings.SITE_URL}{url}"

        # Make the API call based on the method
        try:
            if method == 'GET':
                response = requests.get(
                    url, headers=final_headers, params=final_query_params)
            elif method == 'POST':
                response = requests.post(
                    url, headers=final_headers, json=final_body)
            elif method == 'PUT':
                response = requests.put(
                    url, headers=final_headers, json=final_body)
            elif method == 'DELETE':
                response = requests.delete(
                    url, headers=final_headers, json=final_body)

            response.raise_for_status()  # Raise an error for bad responses
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")
