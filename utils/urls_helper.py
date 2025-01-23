import re
import logging
from django.urls import get_resolver, URLPattern, URLResolver
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

EXCLUDED_APPS = {'admin', 'silk', '', 'define', 'app_builder', 'license'}

def _get_request_methods(callback):
    """
    Determine allowed HTTP methods for a view.
    """
    if hasattr(callback, 'actions'):  # DRF ViewSet
        return list(callback.actions.keys())
    elif hasattr(callback, 'http_method_names'):  # Django/DRF View
        return [method.upper() for method in callback.http_method_names if method != 'options']
    return []


def _get_callback_name(callback):
    """
    Extract the name of the callback function or class.
    """
    if hasattr(callback, 'view_class'):  # DRF ViewSet or View
        return callback.view_class.__name__
    elif hasattr(callback, 'cls'):  # Django CBV
        return callback.cls.__name__
    elif callable(callback):  # FBV or other callable
        return callback.__name__
    return "UnknownCallback"


def _get_path_parameters(pattern):
    """
    Extract path parameters from a URL pattern and format them.
    """
    parameters = re.findall(r"\(\?P<(\w+)>[^\)]+\)", pattern)
    formatted_pattern = re.sub(r"\(\?P<(\w+)>[^\)]+\)", r"<\1>", pattern)
    formatted_pattern = re.sub(r"\\\.", ".", formatted_pattern)  # Replace escaped dots
    formatted_pattern = re.sub(r"^\^|\$$", "", formatted_pattern)  # Remove start/end markers
    return parameters, formatted_pattern


def _get_view_class(callback):
    """
    Helper to extract the actual class from callback references
    (e.g. DRF ViewSet, Django CBV, or FBV).
    """
    if hasattr(callback, 'view_class'):  # DRF ViewSet or generic APIView
        return callback.view_class
    elif hasattr(callback, 'cls'):  # Django CBV
        return callback.cls
    else:
        # Possibly a function-based view
        return callback


def _get_request_keys(callback):
    """
    Extract expected request keys by introspecting the view’s serializer_class.
    This avoids calling get_serializer() directly on an un-instantiated view.
    """
    view_class = _get_view_class(callback)

    # 1. Grab the serializer_class if it exists
    serializer_class = getattr(view_class, 'serializer_class', None)
    if not serializer_class:
        return []

    # 2. Instantiate the serializer (no request context)
    try:
        serializer = serializer_class()
    except Exception as e:
        logger.error(f"Could not instantiate serializer_class {serializer_class}: {e}")
        return []

    # 3. Inspect its fields
    if hasattr(serializer, 'Meta'):
        # If 'fields' is set to '__all__' and it's a ModelSerializer
        if getattr(serializer.Meta, 'fields', None) == '__all__':
            model = getattr(serializer.Meta, 'model', None)
            if model is not None and hasattr(model, '_meta'):
                return [field.name for field in model._meta.fields]

        # Otherwise, if Meta.fields is a list or tuple
        meta_fields = getattr(serializer.Meta, 'fields', None)
        if meta_fields:
            return list(meta_fields)

    # Fallback to serializer.fields if no Meta or fields
    if hasattr(serializer, 'fields'):
        return list(serializer.fields.keys())

    return []


def _get_query_params(callback):
    """
    Extract expected query parameters by introspecting the same serializer_class,
    OR by checking known attributes like 'query_parameters', 'filterset_fields', etc.
    """
    view_class = _get_view_class(callback)

    # 1) Check for a custom query_parameters attribute
    if hasattr(view_class, 'query_parameters'):
        # e.g. in your view: query_parameters = ['search', 'status', 'ordering']
        return list(view_class.query_parameters)

    # 2) If you use django-filter with filterset_fields
    if hasattr(view_class, 'filterset_fields'):
        # e.g. filterset_fields = ['id', 'name', 'status']
        return list(view_class.filterset_fields)

    # 3) If you use django-filter with a custom filterset_class
    #    you'd have to introspect the filterset_class itself
    if hasattr(view_class, 'filterset_class'):
        fs_class = view_class.filterset_class
        # This is more advanced; you'd need to parse fs_class.Meta.fields, etc.
        if hasattr(fs_class, 'Meta') and hasattr(fs_class.Meta, 'fields'):
            # fields could be a dict or list
            if isinstance(fs_class.Meta.fields, dict):
                # e.g. {'field_name': ['exact', 'icontains']}
                return list(fs_class.Meta.fields.keys())
            elif isinstance(fs_class.Meta.fields, list):
                return fs_class.Meta.fields
        # or the filterset may define filters as class attributes
        # in which case you can look at fs_class.declared_filters.keys()

    # 4) If your code uses DRF’s built-in 'search_fields' or 'ordering_fields'
    if hasattr(view_class, 'search_fields'):
        # e.g. search_fields = ['name', 'description']
        # Typically these come from e.g. SearchFilter
        return list(view_class.search_fields)

    if hasattr(view_class, 'ordering_fields'):
        # e.g. ordering_fields = ['id', 'created_at']
        return list(view_class.ordering_fields)

    # 5) If you want to guess from the serializer’s read_only fields
    #    This is an optional fallback if you have no other data.
    serializer_class = getattr(view_class, 'serializer_class', None)
    if serializer_class is not None:
        try:
            serializer = serializer_class()
            if hasattr(serializer, 'fields'):
                # e.g. consider read_only + not required fields as "query params"
                return [
                    field_name for field_name, field in serializer.fields.items()
                    if getattr(field, 'read_only', False) and not getattr(field, 'required', False)
                ]
        except Exception as e:
            logger.error(f"Could not instantiate serializer_class {serializer_class}: {e}")
            # fallback to empty

    # Default empty if none of the above patterns apply
    return []


def _get_permissions(callback):
    """
    Extract permission classes for a view, including DRF class-based views.
    """
    view_class = _get_view_class(callback)

    # Check if permission_classes is defined on the class or function
    if hasattr(view_class, 'permission_classes'):
        return [perm.__name__ for perm in view_class.permission_classes]
    return []


def get_categorized_urls(application_name=None):
    """
    Categorizes URLs with detailed, readable, and valuable information:
    - Request types
    - Cleaned paths
    - Path parameters
    - Query parameters
    - Permissions
    - Keys (expected body fields)
    - Callback name

    Returns:
        dict: {
          "total_applications": <int>,
          "total_urls": <int>,
          "applications": {
              "<app_name>": [ { ...URL info... }, ... ],
              ...
          }
        }
    """
    urlconf = get_resolver()  # Get the root resolver
    categorized_urls = {}

    def _extract_urls(patterns, prefix=''):
        for pattern in patterns:
            if isinstance(pattern, URLPattern):  # Static route
                # Derive an "application name" from the prefix
                app_name = prefix.split('/')[0] if '/' in prefix else prefix

                # Exclude apps in EXCLUDED_APPS
                if app_name in EXCLUDED_APPS:
                    continue

                # If application_name is specified, skip if it doesn't match
                if application_name and app_name != application_name:
                    continue

                parameters, cleaned_path = _get_path_parameters(str(pattern.pattern))
                details = {
                    'path': prefix + cleaned_path,
                    'name': pattern.name or '',
                    'methods': _get_request_methods(pattern.callback),
                    'callback': _get_callback_name(pattern.callback),
                    'parameters': parameters,
                    'keys': _get_request_keys(pattern.callback),
                    'query_params': _get_query_params(pattern.callback),
                    'permissions': _get_permissions(pattern.callback),
                }

                if app_name not in categorized_urls:
                    categorized_urls[app_name] = []
                categorized_urls[app_name].append(details)

            elif isinstance(pattern, URLResolver):  # Nested resolver
                # Build up the prefix
                app_prefix = prefix + str(pattern.pattern)
                _extract_urls(pattern.url_patterns, app_prefix)

    _extract_urls(urlconf.url_patterns)

    # Optionally add dynamic apps from settings
    try:
        from scohaz_platform.settings import CUSTOM_APPS  # or your own settings
        for app_name in CUSTOM_APPS:
            # Exclude apps in EXCLUDED_APPS
            if app_name in EXCLUDED_APPS:
                continue

            # If application_name is specified, skip if it doesn't match
            if application_name and app_name != application_name:
                continue

            if app_name not in categorized_urls:
                categorized_urls[app_name] = []
            categorized_urls[app_name].append({
                'path': f'{app_name}/',
                'name': f'{app_name}_root',
                'methods': ['GET'],  # example default
                'callback': None,
                'parameters': [],
                'keys': [],
                'query_params': [],
                'permissions': [],
            })
    except ImportError:
        logger.warning("CUSTOM_APPS not found in settings (skip dynamic URLs).")

    # --- Compute totals ---
    total_applications = len(categorized_urls)
    total_urls = sum(len(url_list) for url_list in categorized_urls.values())

    return {
        'total_applications': total_applications,
        'total_urls': total_urls,
        'applications': categorized_urls,
    }


def get_all_urls():
    """
    Extracts all static and dynamic URLs in the project.
    """
    urlconf = get_resolver()  # Get the root resolver
    urls = []

    def _extract_urls(patterns, prefix=''):
        for pattern in patterns:
            if isinstance(pattern, URLPattern):  # Static route
                urls.append({
                    'path': prefix + str(pattern.pattern),
                    'name': pattern.name or '',
                    'callback': pattern.callback.__name__ if hasattr(pattern.callback, '__name__') else '',
                })
            elif isinstance(pattern, URLResolver):  # Nested resolver
                _extract_urls(pattern.url_patterns, prefix + str(pattern.pattern))

    _extract_urls(urlconf.url_patterns)

    # Optionally add dynamic app URLs from your settings
    try:
        from scohaz_platform.settings import CUSTOM_APPS
        for app_name in CUSTOM_APPS:
            urls.append({
                'path': f'{app_name}/',
                'name': f'{app_name}_root',
                'callback': '',
            })
    except ImportError:
        logger.warning("CUSTOM_APPS not found in settings (skip dynamic URLs).")

    return urls
