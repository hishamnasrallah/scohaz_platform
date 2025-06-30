
from django.utils.deprecation import MiddlewareMixin
# from reporting.models import IntegrationConfig
# In your utils or middleware.py file
import threading

        
def get_current_user():
    """
    Retrieve the current user from thread-local storage.
    """
    return getattr(thread_local, 'current_user', None)

# Thread-local storage to capture the current user
thread_local = threading.local()
class CurrentUserMiddleware(MiddlewareMixin):
    """
    Middleware to store the current user in thread-local storage.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        thread_local.current_user = request.user
        print(f"User in middleware: {request.user.username}")  # Debugging line
        response = self.get_response(request)
        return response

        

class DynamicModelMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Add logic to handle requests dynamically
        if request.path.startswith('/reporting/'):
            print(f"Processing request for reporting: {request.path}")

    def process_response(self, request, response):
        # Add logic to handle responses dynamically
        if request.path.startswith('/reporting/'):
            print(f"Processing response for reporting: {response.status_code}")
        return response
