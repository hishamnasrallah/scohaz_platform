from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from integration.models import Integration


class CallIntegrationView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request, integration_id):
        try:
            integration = Integration.objects.get(id=integration_id)

            # Prepare optional parameters
            body = request.data.get(
                'body', None)  # Body can be passed in the request
            query_params = request.data.get(
                'query_params', None)  # Query params can be passed in the request
            headers = request.data.get(
                'headers', None)  # Additional headers can be passed

            # Make the API request using the new method
            response = integration.make_api_request(
                body=body, query_params=query_params, headers=headers)

            return Response(response, status=status.HTTP_200_OK)
        except Integration.DoesNotExist:
            return Response(
                {'error': 'Integration not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
