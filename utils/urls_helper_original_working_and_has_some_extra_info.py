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
        # actions is a dict: {'get': 'list', 'post': 'create', ...}
        # Return the uppercase method names: ['GET','POST', ...]
        return [method.upper() for method in callback.actions.keys()]
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
    Extract expected request keys by introspecting the view's serializer_class,
    removing excluded fields. Also return other_info if present.
    The function returns a dict:
        {
          "keys": [ { "name": <field_name>, "type": <field_type> }, ... ],
          "other_info": <dict or "not written yet">
        }
    """
    excluded_fields = {"id", "created_at", "created_by", "updated_at", "updated_by"}
    view_class = _get_view_class(callback)

    # 1) Gather other_info from the view (if it's a dict with 'keys' sub-dict).
    other_info_attr = getattr(view_class, 'other_info', None)
    if isinstance(other_info_attr, dict):
        tmp_info = dict(other_info_attr)
        custom_keys_dict = tmp_info.pop("keys", None)  # might be another dict
    else:
        tmp_info = None
        custom_keys_dict = None

    # 2) Try to gather serializer-based fields
    serializer_class = getattr(view_class, 'serializer_class', None)
    if not serializer_class:
        # no serializer => fallback
        return _build_final_keys([], custom_keys_dict, tmp_info, excluded_fields)

    try:
        serializer = serializer_class()
    except Exception as e:
        logger.error(f"Could not instantiate serializer_class {serializer_class}: {e}")
        return _build_final_keys([], custom_keys_dict, tmp_info, excluded_fields)

    model = getattr(getattr(serializer, 'Meta', None), 'model', None)
    meta_fields = getattr(getattr(serializer, 'Meta', None), 'fields', None)

    def build_fields_list(field_names):
        field_list = []
        for field_name in field_names:
            if field_name in excluded_fields:
                continue
            if model and hasattr(model, '_meta'):
                try:
                    model_field = model._meta.get_field(field_name)
                    field_type = model_field.get_internal_type()  # e.g. CharField
                except Exception:
                    ser_field = serializer.fields.get(field_name)
                    field_type = type(ser_field).__name__ if ser_field else "Unknown"
            else:
                ser_field = serializer.fields.get(field_name)
                field_type = type(ser_field).__name__ if ser_field else "Unknown"

            field_list.append({"name": field_name, "type": field_type})
        return field_list

    # Collect fields from the serializer
    if meta_fields == '__all__' and model and hasattr(model, '_meta'):
        all_model_field_names = [f.name for f in model._meta.fields]
        serializer_keys = build_fields_list(all_model_field_names)
    elif isinstance(meta_fields, (list, tuple)):
        serializer_keys = build_fields_list(meta_fields)
    elif hasattr(serializer, 'fields'):
        serializer_keys = build_fields_list(serializer.fields.keys())
    else:
        serializer_keys = []

    return _build_final_keys(serializer_keys, custom_keys_dict, tmp_info, excluded_fields)


def _build_final_keys(serializer_keys, custom_keys_dict, leftover_other_info, excluded_fields):
    """
    Decide the final structure of:
      {
        "keys": [...],
        "other_info": ...
      }
    """

    # STEP A: Determine final keys
    if serializer_keys:
        final_keys = serializer_keys
    else:
        # If serializer_keys is empty, we can fallback to custom_keys_dict
        if isinstance(custom_keys_dict, dict) and custom_keys_dict:
            filtered = []
            for field_name, field_type in custom_keys_dict.items():
                if field_name not in excluded_fields:
                    filtered.append({"name": field_name, "type": field_type})
            final_keys = filtered
        else:
            final_keys = []

    # STEP B: Determine final other_info
    if isinstance(leftover_other_info, dict) and leftover_other_info:
        final_other_info = leftover_other_info
    else:
        final_other_info = "not written yet"

    return {
        "keys": final_keys,
        "other_info": final_other_info
    }


def _get_query_params(callback):
    """
    Extract expected query parameters by introspecting known attributes:
    query_parameters, filterset_fields, filterset_class, search_fields, ordering_fields, etc.
    """
    view_class = _get_view_class(callback)

    if hasattr(view_class, 'query_parameters'):
        return list(view_class.query_parameters)

    if hasattr(view_class, 'filterset_fields'):
        return list(view_class.filterset_fields)

    if hasattr(view_class, 'filterset_class'):
        fs_class = view_class.filterset_class
        if hasattr(fs_class, 'Meta') and hasattr(fs_class.Meta, 'fields'):
            if isinstance(fs_class.Meta.fields, dict):
                return list(fs_class.Meta.fields.keys())
            elif isinstance(fs_class.Meta.fields, list):
                return fs_class.Meta.fields

    if hasattr(view_class, 'search_fields'):
        return list(view_class.search_fields)

    if hasattr(view_class, 'ordering_fields'):
        return list(view_class.ordering_fields)

    # last resort: no known query params
    return []


def _get_permissions(callback):
    """
    Extract permission classes for a view, including DRF class-based views.
    """
    view_class = _get_view_class(callback)
    if hasattr(view_class, 'permission_classes'):
        return [perm.__name__ for perm in view_class.permission_classes]
    return []


def _build_sample_value(field_type):
    """
    Given a field_type (e.g. 'CharField', 'IntegerField') return a default sample value.
    """
    ftype_lower = field_type.lower()
    if 'char' in ftype_lower or 'text' in ftype_lower:
        return "Sample text"
    elif 'int' in ftype_lower:
        return 123
    elif 'bool' in ftype_lower:
        return True
    elif 'decimal' in ftype_lower or 'float' in ftype_lower:
        return 99.99
    else:
        return "example"


def _build_methods_info(methods, keys):
    """
    For each HTTP method, build a small schema:
       {
         "GET": {
           "description": "Retrieve data",
           "status_codes": [...],
           "request_example": {...},
           "response_example": {...}
         },
         "POST": ...
       }
    We'll generate placeholder request/response examples from 'keys'.
    """
    methods_info = {}

    # Pre-generate sample dictionaries for request & response
    # based on the keys we have
    sample_request = {}
    sample_response = {}
    for field in keys:
        field_name = field["name"]
        field_type = field["type"]
        sample_value = _build_sample_value(field_type)
        sample_request[field_name] = sample_value
        sample_response[field_name] = sample_value

    for method in methods:
        method_upper = method.upper()
        if method_upper == 'GET':
            methods_info['GET'] = {
                "description": "Retrieve a list or single resource",
                "status_codes": [
                    {"code": 200, "description": "OK"},
                    {"code": 404, "description": "Not Found"},
                    {"code": 401, "description": "Unauthorized"},
                ],
                "request_example": None,  # GET typically doesn't send a body
                "response_example": {
                    "count": 1,
                    "results": [sample_response]
                }
            }
        elif method_upper == 'POST':
            methods_info['POST'] = {
                "description": "Create a new resource",
                "status_codes": [
                    {"code": 201, "description": "Created"},
                    {"code": 400, "description": "Validation Error"},
                    {"code": 401, "description": "Unauthorized"},
                ],
                "request_example": sample_request,
                "response_example": sample_response
            }
        elif method_upper == 'PUT':
            methods_info['PUT'] = {
                "description": "Update an entire resource (replace all fields)",
                "status_codes": [
                    {"code": 200, "description": "Updated"},
                    {"code": 400, "description": "Validation Error"},
                    {"code": 404, "description": "Not Found"},
                ],
                "request_example": sample_request,
                "response_example": sample_response
            }
        elif method_upper == 'PATCH':
            methods_info['PATCH'] = {
                "description": "Partially update a resource (some fields)",
                "status_codes": [
                    {"code": 200, "description": "Updated"},
                    {"code": 400, "description": "Validation Error"},
                    {"code": 404, "description": "Not Found"},
                ],
                "request_example": {
                    # For patch, let's just show one field as an example
                    # or we can do the entire set if you prefer
                    list(sample_request.keys())[0]: list(sample_request.values())[0]
                }if len(list(sample_request.keys())) == len(list(sample_request.values())) and len(list(sample_request.keys())) > 0 else {},
                "response_example": sample_response
            }
        elif method_upper == 'DELETE':
            methods_info['DELETE'] = {
                "description": "Delete a resource",
                "status_codes": [
                    {"code": 204, "description": "No Content"},
                    {"code": 404, "description": "Not Found"},
                ],
                "request_example": None,
                "response_example": None
            }
        else:
            # fallback for any uncommon method (HEAD, OPTIONS, etc.)
            methods_info[method_upper] = {
                "description": f"{method_upper} operation",
                "status_codes": [],
                "request_example": sample_request,
                "response_example": sample_response
            }

    return methods_info


def get_categorized_urls(application_name=None):
    """
    Returns a dictionary of the form:
    {
      'total_applications': X,
      'total_urls': Y,
      'applications': {
         'app1': [
            {
              'path': ...,
              'name': ...,
              'methods': [...],
              'parameters': [...],
              'keys': [...],
              'other_info': ...,
              'query_params': [...],
              'permissions': [...],
              'methods_info': {  # <-- new: deeper doc per HTTP method
                 'GET': {
                   'description': 'Retrieve data',
                   'status_codes': [ {code, description}, ...],
                   'request_example': ...,
                   'response_example': ...
                 },
                 'POST': ...
              }
            },
            ...
         ]
      }
    }
    """
    urlconf = get_resolver()  # Get the root resolver
    categorized_urls = {}

    def _extract_urls(patterns, prefix=''):
        for pattern in patterns:
            if isinstance(pattern, URLPattern):
                # Build the app_name from prefix
                app_name = prefix.split('/')[0] if '/' in prefix else prefix

                # Exclude apps in EXCLUDED_APPS
                if app_name in EXCLUDED_APPS:
                    continue

                # If application_name is specified, skip if it doesn't match
                if application_name and app_name != application_name:
                    continue

                parameters, cleaned_path = _get_path_parameters(str(pattern.pattern))
                raw_path = prefix + str(pattern.pattern)

                # Skip certain auto-generated or unwanted paths
                if "drf_format_suffix" in raw_path:
                    continue
                if "(?P<format>[a-z0-9]+)/?$" in raw_path:
                    continue
                if "custom-action" in raw_path:
                    continue
                if "validation-rules" in raw_path:
                    continue
                if "integration-configs" in raw_path:
                    continue

                # Also skip if the path is exactly `app_name/` (like "crm/") if you want
                if cleaned_path.strip('/') == app_name.strip('/'):
                    continue

                # Collect keys, other_info, query_params, etc.
                keys_and_info = _get_request_keys(pattern.callback)
                keys = keys_and_info["keys"]
                other_info = keys_and_info["other_info"]
                query_params = _get_query_params(pattern.callback)
                permissions = _get_permissions(pattern.callback)
                methods = _get_request_methods(pattern.callback)

                # Build deeper info per method
                methods_info = _build_methods_info(methods, keys)

                details = {
                    'path': prefix + cleaned_path,
                    'name': pattern.name or '',
                    'methods': methods,
                    'parameters': parameters,
                    'keys': keys,         # derived from serializer or other_info
                    'other_info': other_info,
                    'query_params': query_params,
                    'permissions': permissions,
                    'methods_info': methods_info  # <--- newly added
                }

                if app_name not in categorized_urls:
                    categorized_urls[app_name] = []
                categorized_urls[app_name].append(details)

            elif isinstance(pattern, URLResolver):
                app_prefix = prefix + str(pattern.pattern)
                _extract_urls(pattern.url_patterns, app_prefix)

    # Traverse the URL patterns
    _extract_urls(urlconf.url_patterns)

    # Optionally handle dynamic or custom apps from settings
    try:
        from scohaz_platform.settings import CUSTOM_APPS
        for app_name_ in CUSTOM_APPS:
            if app_name_ in EXCLUDED_APPS:
                continue
            if application_name and app_name_ != application_name:
                continue
            if app_name_ not in categorized_urls:
                # If you want to add a stub if none found
                categorized_urls[app_name_] = []
    except ImportError:
        logger.warning("CUSTOM_APPS not found in settings (skip dynamic URLs).")

    # Compute totals
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
