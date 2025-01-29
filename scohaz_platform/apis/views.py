from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated  # Optional: Adjust permissions as needed


from utils.urls_helper import get_all_urls, get_categorized_urls


class ApplicationURLsView(APIView):
    """
    API endpoint to retrieve all application URLs.
    """
    permission_classes = [IsAuthenticated]  # Adjust permissions

    def get(self, request, *args, **kwargs):
        urls = get_all_urls()
        return Response({'applications': urls})



class CategorizedApplicationURLsView(APIView):
    """
    API endpoint to retrieve categorized application URLs with detailed information.
    """
    permission_classes = [IsAuthenticated]  # Adjust permissions

    def get(self, request, *args, **kwargs):
        application_name = request.query_params.get('application_name', None)
        categorized_urls = get_categorized_urls(application_name=application_name)
        return Response({'applications': categorized_urls})
