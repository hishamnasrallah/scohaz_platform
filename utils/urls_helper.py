import re
import logging

from django.db.models import NOT_PROVIDED
from django.urls import get_resolver, URLPattern, URLResolver
from django.utils import timezone
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

EXCLUDED_APPS = {'admin', 'silk', '', 'define', 'app_builder', 'license', 'reporting'}


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
          "keys": [ { "name": <field_name>, "type": <field_type>, ... }, ... ],
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

            # We'll attempt to get a model_field and a serializer_field
            model_field = None
            ser_field = serializer.fields.get(field_name, None)

            if model and hasattr(model, '_meta'):
                try:
                    model_field = model._meta.get_field(field_name)
                except Exception:
                    # If it's not found in the model, we still have ser_field as fallback
                    pass

            # We'll figure out the field_type name as before
            if model_field:
                field_type = model_field.get_internal_type()  # e.g. CharField
            else:
                field_type = type(ser_field).__name__ if ser_field else "Unknown"

            # ---------------------------------------------------------------------
            # METADATA: required, read_only, default, help_text
            # (from previous point)
            # ---------------------------------------------------------------------
            required = False
            read_only = False
            default_value = None
            help_text = ""
            choices_list = []

            if model_field:
                required = (not model_field.null) and (not model_field.blank)
                if model_field.default is not NOT_PROVIDED:
                    default_value = model_field.default
                help_text = getattr(model_field, 'help_text', '') or ''

            # -- NEW: If we have choices
            try:
                if model_field.choices:
                    for (val, lbl) in model_field.choices:
                        choices_list.append({"value": val, "label": lbl})
            except:
                pass

            if ser_field:
                if hasattr(ser_field, 'read_only') and ser_field.read_only:
                    read_only = True
                if hasattr(ser_field, 'help_text') and ser_field.help_text:
                    help_text = ser_field.help_text

            # Build the base field_info
            field_info = {
                "name": field_name,
                "type": field_type,
                "required": required,
                "read_only": read_only,
                "default": default_value,
                "help_text": help_text
            }
            if choices_list:
                field_info["choices"] = choices_list

            # ---------------------------------------------------------------------
            # RELATIONSHIP DETAILS - ADDED
            # ---------------------------------------------------------------------
            if model_field and model_field.is_relation:
                relation_type = model_field.get_internal_type()
                remote_model = model_field.remote_field.model
                related_model = f"{remote_model._meta.app_label}.{remote_model._meta.model_name}"

                field_info["relation_type"] = relation_type
                field_info["related_model"] = related_model

                # NEW: Handle ManyToManyField as multiple select
                if relation_type == 'ManyToManyField':
                    field_info["multiple"] = True  # <-- Important for frontend to show multi-select
                    field_info["required"] = model_field.blank is False

                # Optional: add limit_choices_to
                limit_choices = getattr(model_field.remote_field, 'limit_choices_to', None)
                if limit_choices:
                    field_info["limit_choices_to"] = str(limit_choices)

                # Optional: extract choices from model field (if defined)
                if model_field.choices:
                    choices_list = []
                    for (value, label) in model_field.choices:
                        choices_list.append({"value": value, "label": label})
                    field_info["choices"] = choices_list

        # Append to field_list
            field_list.append(field_info)

        return field_list

    # Collect fields from the serializer
    if meta_fields == '__all__' and model and hasattr(model, '_meta'):
        all_model_field_names = [f.name for f in model._meta.fields] + \
                                [f.name for f in model._meta.many_to_many]
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
                } if len(sample_request.keys()) > 0 else {},
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


def get_categorized_urls(application_name=None, user=None):  # <-- ADDED: user param
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
              'methods_info': {
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
    from django.urls import get_resolver
    urlconf = get_resolver()  # Get the root resolver
    categorized_urls = {}

    def _extract_urls(patterns, prefix=''):
        for pattern in patterns:
            if isinstance(pattern, URLPattern):
                # Build the app_name from prefix
                app_name = prefix.split('/')[0] if '/' in prefix else prefix

                # Exclude apps in EXCLUDED_APPS - check both prefix and actual app
                if app_name in EXCLUDED_APPS:
                    continue

                # Also check if this URL belongs to an excluded app by checking the view's module
                if hasattr(pattern.callback, '__module__'):
                    module_parts = pattern.callback.__module__.split('.')
                    if module_parts[0] in EXCLUDED_APPS:
                        continue

                # If application_name is specified, skip if it doesn't match
                if application_name and app_name != application_name:
                    continue

                parameters, cleaned_path = _get_path_parameters(str(pattern.pattern))
                raw_path = prefix + str(pattern.pattern)

                # Skip certain auto-generated or unwanted paths
                # if "drf_format_suffix" in raw_path:
                #     continue
                # if "auth" in raw_path:
                #     continue
                # if "case" in raw_path:
                #     continue
                # if "api-docs" in raw_path:
                #     continue
                # if "version" in raw_path:
                #     continue
                # if "integration" in raw_path:
                #     continue
                # if "app-builder" in raw_path:
                #     continue
                # if "translations" in raw_path:
                #     continue
                # if "(?P<format>[a-z0-9]+)/?$" in raw_path:
                #     continue
                # if "custom-action" in raw_path:
                #     continue
                # if "validation-rules" in raw_path:
                #     continue
                # if "integration-configs" in raw_path:
                #     continue
                # if "api-root" in  str(pattern.name):
                #     continue
                EXCLUDED_PATHS = {
                    "drf_format_suffix",
                    "auth",
                    "case",
                    "api-docs",
                    "version",
                    "integration",
                    "app-builder",
                    "translations",
                    "custom-action",
                    "validation-rules",
                    "integration-configs",
                }

                EXCLUDED_PATTERNS = {
                    "(?P<format>[a-z0-9]+)/?$",
                    "api-root"
                }

                if any(excluded in raw_path for excluded in EXCLUDED_PATHS) or \
                        any(excluded in str(pattern.name) if pattern.name else "" for excluded in EXCLUDED_PATTERNS):
                    continue
                # Also skip if the path is exactly `app_name/` (like "crm/") if you want
                if cleaned_path.strip('/') == app_name.strip('/'):
                    continue

                # --------------------------------------------------
                # NEW: Identify the model/content_type and check CRUDPermission
                # --------------------------------------------------
                from django.contrib.contenttypes.models import ContentType
                from authentication.models import CRUDPermission  # <-- ADJUST import path as needed

                view_class = _get_view_class(pattern.callback)
                try:
                    model_cls = getattr(view_class.serializer_class.Meta, 'model', None)
                except:
                    model_cls = None

                if not model_cls:
                    # Sometimes it's on .queryset.model
                    queryset = getattr(view_class, 'queryset', None)
                    if queryset is not None and hasattr(queryset, 'model'):
                        model_cls = queryset.model

                # Default: user cannot do anything
                can_create = can_read = can_update = can_delete = False

                content_type = None
                if model_cls:
                    print(model_cls)
                if model_cls:
                    content_type = ContentType.objects.get_for_model(model_cls)

                if user and content_type:
                    # fetch all CRUDPermission for user groups & this content_type with context='api'
                    perms_qs = CRUDPermission.objects.filter(
                        group__in=user.groups.all(),
                        content_type=content_type,
                        context__contains='api'
                    )
                    if perms_qs.exists():
                        can_create = any(p.can_create for p in perms_qs)
                        can_read   = any(p.can_read   for p in perms_qs)
                        can_update = any(p.can_update for p in perms_qs)
                        can_delete = any(p.can_delete for p in perms_qs)
                else:
                    # No user or no identified model => fallback logic
                    # e.g. allow read to everyone, or disallow everything
                    can_read = True  # as an example

                # If user cannot read => skip entire endpoint
                if not can_read:
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

                # Filter out disallowed methods
                allowed_methods = set(methods)
                if not can_create:
                    allowed_methods.discard('POST')
                if not can_read:
                    allowed_methods.discard('GET')
                if not can_update:
                    allowed_methods.discard('PUT')
                    allowed_methods.discard('PATCH')
                if not can_delete:
                    allowed_methods.discard('DELETE')

                final_methods = list(allowed_methods)
                filtered_methods_info = {
                    m: methods_info[m] for m in final_methods if m in methods_info
                }

                details = {
                    'path': prefix + cleaned_path,
                    'name': pattern.name or '',
                    'methods': final_methods,
                    'parameters': parameters,
                    'keys': keys,         # derived from serializer or other_info
                    'other_info': other_info,
                    'query_params': query_params,
                    'permissions': permissions,  # DRF permission classes
                    'methods_info': filtered_methods_info
                }

                # --------------------------------------------------
                # NEW: Add "available_actions" field  # <-- ADDED
                # --------------------------------------------------
                available_actions = []  # <-- ADDED
                if can_read and "GET" in final_methods:          # <-- ADDED
                    available_actions.append("read")
                if can_create and "POST" in final_methods:          # <-- ADDED
                    available_actions.append("create")
                if can_update and ("PUT" in final_methods or "PATCH" in final_methods):          # <-- ADDED
                    available_actions.append("update")
                if can_delete and "DELETE" in final_methods:          # <-- ADDED
                    available_actions.append("delete")
                # you could also add "view" if can_read is True, but typically
                # it's implied by the fact we didn't skip the endpoint

                details["available_actions"] = available_actions  # <-- ADDED

                if app_name not in categorized_urls:
                    categorized_urls[app_name] = []
                categorized_urls[app_name].append(details)

            elif isinstance(pattern, URLResolver):
                app_prefix = prefix + str(pattern.pattern)
                _extract_urls(pattern.url_patterns, app_prefix)

    # Traverse the URL patterns
    _extract_urls(urlconf.url_patterns, prefix='')

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
        "api_version": "v1.0.0",                   # <-- ADDED
        "schema_generated_on": timezone.now().isoformat(),
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
