# scohaz_platform/middleware.py

from importlib import import_module
from django.urls import resolve
from django.conf import settings


class CurrentUserRouterMiddleware:
    """
    Middleware to set thread_local.current_user per app before view logic runs.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        resolver_match = resolve(request.path_info)
        app_name = resolver_match.app_name

        if app_name == "admin":
            app_name = self.get_app_from_admin_context(request)

        self.process_current_user_middleware(request, app_name)
        return self.get_response(request)

    def get_app_from_admin_context(self, request):
        try:
            parts = request.path.split("/")
            if len(parts) > 2 and parts[1] == "admin":
                return parts[2]
        except Exception as e:
            print(f"[CurrentUserRouter] Error detecting admin app: {e}")
        return None

    def process_current_user_middleware(self, request, app_name):
        try:
            if app_name:
                for middleware_path in settings.APPS_CURRENT_USER_MIDDLEWARE.get(app_name, []):
                    self.load_and_execute_middleware(middleware_path, request)
                    break  # Only one user middleware per app
        except Exception as e:
            print(f"[CurrentUserRouter] Error: {e}")

    def load_and_execute_middleware(self, middleware_path, request):
        try:
            module_path, class_name = middleware_path.rsplit(".", 1)
            middleware_class = getattr(import_module(module_path), class_name)
            middleware_instance = middleware_class(lambda req: None)
            middleware_instance.process_request(request)
        except Exception as e:
            print(f"[CurrentUserRouter] Failed to load middleware {middleware_path}: {e}")

# class MiddlewareRouter:
#     def __init__(self, get_response):
#         self.get_response = get_response
#
#     def __call__(self, request):
#         # Ensure global middlewares (e.g., AuthenticationMiddleware) run first
#         response = self.get_response(request)
#
#         # Resolve app name
#         resolver_match = resolve(request.path_info)
#         app_name = resolver_match.app_name
#
#         # Skip processing for jsi18n or other excluded apps
#         if app_name in ["jsi18n"]:
#             print(f"Skipping middleware processing for app: {app_name}")
#             return response
#
#         # Handle admin app requests
#         if app_name == "admin":
#             app_name = self.get_app_from_admin_context(request)
#
#         # Execute app-specific dynamic model middlewares
#         self.process_app_specific_middlewares(request, app_name)
#
#         # Execute app-specific user middlewares
#         self.process_user_middleware(request, app_name)
#
#         return response
#
#     def get_app_from_admin_context(self, request):
#         """
#         Infer the app name from the admin request context.
#         """
#         try:
#             # Extract the app_label from the admin request path
#             path_parts = request.path.split("/")
#             if len(path_parts) > 2 and path_parts[1] == "admin":
#                 # Example: /admin/accounting/modelname/
#                 app_label = path_parts[2]
#                 return app_label
#         except Exception as e:
#             print(f"Error inferring app from admin context: {e}")
#         return None
#
#     def process_app_specific_middlewares(self, request, app_name):
#         """
#         Dynamically load and execute middlewares for the resolved app.
#         """
#         try:
#             if app_name and app_name in settings.APP_MIDDLEWARE_MAPPING:
#                 for middleware_path in settings.APP_MIDDLEWARE_MAPPING[app_name]:
#                     print(f"Executing DynamicModelMiddleware: {middleware_path}")  # Debugging
#                     self.load_and_execute_middleware(middleware_path, request)
#         except Exception as e:
#             print(f"MiddlewareRouter Error (DynamicModelMiddleware): {e}")
#
#     def process_user_middleware(self, request, app_name):
#         """
#         Dynamically load and execute user middleware for the resolved app.
#         """
#         try:
#             if app_name:
#                 for middleware_path in settings.APPS_CURRENT_USER_MIDDLEWARE:
#                     if middleware_path.startswith(f"{app_name}."):
#                         self.load_and_execute_middleware(middleware_path, request)
#         except Exception as e:
#             print(f"MiddlewareRouter Error (CurrentUserMiddleware): {e}")
#
#     def load_and_execute_middleware(self, middleware_path, request):
#         """
#         Dynamically load and execute the middleware.
#         """
#         try:
#             module_path, class_name = middleware_path.rsplit(".", 1)
#             middleware_class = getattr(import_module(module_path), class_name)
#             middleware_instance = middleware_class(lambda req: None)
#             middleware_instance(request)
#         except (ImportError, AttributeError) as e:
#             print(f"Failed to load middleware {middleware_path}: {e}")


class MiddlewareRouter:
    """
    Post-request middleware router for app-specific business logic
    (like model-level triggers, logging, etc.)
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        resolver_match = resolve(request.path_info)
        app_name = resolver_match.app_name

        if app_name in ["jsi18n"]:
            return response

        if app_name == "admin":
            app_name = self.get_app_from_admin_context(request)

        self.process_app_specific_middlewares(request, app_name)
        return response

    def get_app_from_admin_context(self, request):
        try:
            parts = request.path.split("/")
            if len(parts) > 2 and parts[1] == "admin":
                return parts[2]
        except Exception as e:
            print(f"[MiddlewareRouter] Error detecting admin app: {e}")
        return None

    def process_app_specific_middlewares(self, request, app_name):
        try:
            if app_name and app_name in settings.APP_MIDDLEWARE_MAPPING:
                for middleware_path in settings.APP_MIDDLEWARE_MAPPING[app_name]:
                    self.load_and_execute_middleware(middleware_path, request)
        except Exception as e:
            print(f"[MiddlewareRouter] Error (DynamicModelMiddleware): {e}")

    def load_and_execute_middleware(self, middleware_path, request):
        try:
            module_path, class_name = middleware_path.rsplit(".", 1)
            middleware_class = getattr(import_module(module_path), class_name)
            middleware_instance = middleware_class(lambda req: None)
            middleware_instance(request)
        except Exception as e:
            print(f"[MiddlewareRouter] Failed to load middleware {middleware_path}: {e}")