import jwt
from django.conf import settings
from django.http import JsonResponse
from django.utils.timezone import now
from rest_framework.authentication import get_authorization_header
from .models import Subscription, Client, License
from django.contrib.auth import get_user_model

User = get_user_model()


class SubscriptionLicenseMiddleware:
    """
    Middleware to restrict access based on active subscription (for developers) and valid licenses (for clients).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Allow public endpoints
        public_paths = [
            '/admin/', '/login/', '/signup/', '/api/token/', '/docs/',
            '/auth/login/', '/auth/register/'
        ]
        if any(request.path.startswith(path) for path in public_paths):
            return self.get_response(request)

        # Extract Authorization header
        auth_header = get_authorization_header(request).decode('utf-8')
        if not auth_header:
            return JsonResponse({'error': 'Authorization token missing.'}, status=401)

        # Parse JWT token
        try:
            token_type, token = auth_header.split()
            if token_type.lower() != 'bearer':
                raise ValueError("Invalid token type.")
        except ValueError:
            return JsonResponse({'error': 'Invalid Authorization header format.'}, status=401)

        try:
            decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = decoded_token.get('uid')
            project_id = decoded_token.get('project_id')
            if not user_id:
                raise jwt.InvalidTokenError("UID missing in token payload.")

            user = User.objects.get(id=user_id)
            if user.is_superuser:
                request.user = user
                return self.get_response(request)

        except (User.DoesNotExist, jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return JsonResponse({'error': 'Invalid or expired token.'}, status=401)

        # Fetch client based on authenticated user
        try:
            client = Client.objects.get(user=user)
        except Client.DoesNotExist:
            return JsonResponse({'error': 'Client information not found.'}, status=403)

        # Handle Developer (Platform access)
        if user.is_developer:
            subscription = Subscription.objects.filter(client=client, status='active').first()
            if not subscription or not subscription.has_active_subscription():
                return JsonResponse({'error': 'No active subscription. Please subscribe.'}, status=403)
            if subscription.is_user_limit_reached():
                return JsonResponse({'error': 'User/project limit reached for your plan.'}, status=403)
        elif not user.is_developer:
            # Handle Client (Project access)
            # project_id = request.path.split("/")[3]  # Assuming the project ID is part of the URL path
            # // TODO:  handle the public user type by remove client from the query and handle the back office users by add client=client in the next query
            _license = License.objects.filter(client__project_id=project_id, status='active').first()
            if not _license or not _license.has_valid_license_for_project(project_id):
                return JsonResponse({'error': 'No valid license for this project. Please purchase a license.'}, status=403)

        # Grant access
        request.user = user
        return self.get_response(request)
