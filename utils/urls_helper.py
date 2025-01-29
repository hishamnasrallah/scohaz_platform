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
    Extract expected request keys by introspecting the view's serializer_class,
    removing excluded fields. If the serializer has no fields, attempt to use
    other_info["keys"] if available. Also always return "other_info" in the result
    (either the leftover of other_info dict or "not written yet").

    Returns a dict:
      {
        "keys": [ { "name": <field_name>, "type": <field_type> }, ... ],
        "other_info": <dict or "not written yet">
      }
    """
    excluded_fields = {"id", "created_at", "created_by", "updated_at", "updated_by"}
    view_class = _get_view_class(callback)

    # 1) Gather other_info from the view (if it's a dict).
    #    Example:
    #      other_info = {
    #         "keys": {"phone_number": "integer", "status": "ForeignKey"},
    #         "usage": "some usage text"
    #      }
    other_info_attr = getattr(view_class, 'other_info', None)

    # If there's no other_info or it's not a dict, we'll handle that later.
    if isinstance(other_info_attr, dict):
        # Make a copy so we can safely pop "keys"
        tmp_info = dict(other_info_attr)
        custom_keys_dict = tmp_info.pop("keys", None)  # might be another dict
        # Now tmp_info holds the leftover fields from other_info, e.g. {"usage": "something"}
        # We'll decide later if that's empty or not.
    else:
        # No valid other_info => no custom keys
        tmp_info = None
        custom_keys_dict = None

    # 2) Try to gather serializer-based fields
    serializer_class = getattr(view_class, 'serializer_class', None)
    if not serializer_class:
        # No serializer => skip to _build_final_keys with an empty list
        return _build_final_keys([], custom_keys_dict, tmp_info, excluded_fields)

    try:
        serializer = serializer_class()
    except Exception as e:
        logger.error(f"Could not instantiate serializer_class {serializer_class}: {e}")
        return _build_final_keys([], custom_keys_dict, tmp_info, excluded_fields)

    model = getattr(getattr(serializer, 'Meta', None), 'model', None)
    meta_fields = getattr(getattr(serializer, 'Meta', None), 'fields', None)

    def build_fields_list(field_names):
        """
        Convert a list of field names to a list of {name, type}, skipping excluded_fields.
        We'll attempt to get the model field type; fallback to serializer field class name.
        """
        field_list = []
        for field_name in field_names:
            if field_name in excluded_fields:
                continue
            if model and hasattr(model, '_meta'):
                try:
                    model_field = model._meta.get_field(field_name)
                    field_type = model_field.get_internal_type()  # e.g. CharField
                except Exception:
                    # fallback to the serializer field's class name
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

    # Pass everything to the final builder
    return _build_final_keys(serializer_keys, custom_keys_dict, tmp_info, excluded_fields)

def _build_final_keys(serializer_keys, custom_keys_dict, leftover_other_info, excluded_fields):
    """
    Decide the final structure of:
      {
        "keys": [...],
        "other_info": ...
      }

    Logic:
      1. If serializer_keys is not empty, keep them as is.
      2. If serializer_keys is empty and custom_keys_dict is present, use that for keys.
         - Remove excluded fields from custom_keys_dict.
      3. Otherwise, keys = [] (empty).
      4. leftover_other_info is either a dict or None.
         - If it's a dict (with leftover usage, etc.) and not empty, use it for "other_info".
         - Otherwise "other_info" = "not written yet".
    """
    # STEP A: Determine final keys
    if serializer_keys:
        # If the serializer gave us some fields, keep them
        final_keys = serializer_keys
    else:
        # Serializer keys are empty
        if isinstance(custom_keys_dict, dict) and custom_keys_dict:
            # Use the "keys" subdict from other_info
            filtered = []
            for field_name, field_type in custom_keys_dict.items():
                if field_name not in excluded_fields:
                    filtered.append({"name": field_name, "type": field_type})
            final_keys = filtered
        else:
            # No custom keys => empty list
            final_keys = []

    # STEP B: Determine final other_info
    if isinstance(leftover_other_info, dict) and leftover_other_info:
        # leftover_other_info might have had "keys" popped out.
        if leftover_other_info:
            final_other_info = leftover_other_info
        else:
            final_other_info = "not written yet"
    else:
        # Not a dict or empty => "not written yet"
        final_other_info = "not written yet"

    return {
        "keys": final_keys,
        "other_info": final_other_info
    }


def _fallback_keys(view_class):
    """
    Fallback to reading a custom attribute `other_info` if serializer keys are absent.
    If `other_info` not found or empty, return a single 'not written yet' entry.
    """
    other_info = getattr(view_class, 'other_info', None)
    if other_info and isinstance(other_info, list):
        # Build a list of dicts from other_info
        # e.g., if other_info = ["title", "description"], we produce:
        # [{"name": "title", "type": "other_info"}, {"name": "description", "type": "other_info"}]
        return [{"name": name, "type": "other_info"} for name in other_info]
    else:
        # Return a single dict with a "not written yet" message
        return [{"name": "not written yet", "type": "unknown"}]


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

                # -----------------------------------------------------------
                # 1) Skip if "drf_format_suffix" is found in the raw path
                raw_path = prefix + str(pattern.pattern)  # or cleaned_path
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

                # 2) Skip if the path is exactly `app_name/` (e.g. "crm/")
                if cleaned_path.strip('/') == app_name.strip('/'):
                    continue
                # -----------------------------------------------------------
                keys_and_info = _get_request_keys(pattern.callback)

                details = {
                    'path': prefix + cleaned_path,
                    'name': pattern.name or '',
                    'methods': _get_request_methods(pattern.callback),
                    # 'callback': _get_callback_name(pattern.callback),
                    'parameters': parameters,
                    'keys': keys_and_info["keys"],  # a list
                    'other_info': keys_and_info["other_info"],  # a dict or "not written yet"                    'query_params': _get_query_params(pattern.callback),
                    'permissions': _get_permissions(pattern.callback),
                }

                if app_name not in categorized_urls:
                    categorized_urls[app_name] = []
                categorized_urls[app_name].append(details)

            elif isinstance(pattern, URLResolver):
                # Nested resolver
                app_prefix = prefix + str(pattern.pattern)
                _extract_urls(pattern.url_patterns, app_prefix)

    _extract_urls(urlconf.url_patterns)

    # Optionally add dynamic apps from settings
    try:
        from scohaz_platform.settings import CUSTOM_APPS
        for app_name in CUSTOM_APPS:
            if app_name in EXCLUDED_APPS:
                continue
            if application_name and app_name != application_name:
                continue

            # Because these dynamic URLs are often placeholders, many times
            # they might just be `<app_name>/`; if so, skip them if you want.
            # E.g.:
            # if app_name not in categorized_urls and not skip root placeholders:
            if app_name not in categorized_urls:
                categorized_urls[app_name] = []

            # If you want to skip the root path as well:
            # categorized_urls[app_name].append({
            #     'path': f'{app_name}/',
            #     'name': f'{app_name}_root',
            #     'methods': ['GET'],
            #     'callback': None,
            #     'parameters': [],
            #     'keys': [],
            #     'query_params': [],
            #     'permissions': [],
            # })

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
