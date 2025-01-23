# myapp/plugins/default_plugin.py

import json
from django.db import models

def find_records(case, mapper_target):
    """
    A trivial default finder that does no real searching.
    Always returns an empty list or None, meaning 'no existing record found'.
    This means the processor will always create a new record.

    Alternatively, you could do something like:
      - if case.case_data has an 'id' or 'pk', try to find that.
      - or read some filter rules from mapper_target...
    """
    return None

def process_records(case, mapper_target, found_object):
    """
    Example processor that either updates the found_object if it exists,
    or creates a new one if it doesn't,
    using the declared MapperFieldRules for data assignment.
    """
    model_class = mapper_target.content_type.model_class()

    # If we found an object, use it. Otherwise create a new instance
    instance = found_object or model_class()

    # Check if we have any field_rules
    field_rules = mapper_target.field_rules.all()

    for rule in field_rules:
        # Extract data from case.case_data by the rule.json_path
        # For simplicity, assume a dotted path with no array logic
        value = extract_json_value(case.case_data, rule.json_path)

        # If transform_function_path is set, apply it
        if rule.transform_function_path:
            transform_func = load_function_by_path(rule.transform_function_path)
            value = transform_func(value)

        # Assign to instance
        setattr(instance, rule.target_field, value)

    instance.save()
    return instance

def extract_json_value(case_data, path_str):
    """
    Minimal example of a dotted path lookup: e.g. path_str="vacation.start_date"
    """
    keys = path_str.split(".")
    current_val = case_data
    for k in keys:
        if current_val is None:
            return None
        if k not in current_val:
            return None
        current_val = current_val[k]
    return current_val

def load_function_by_path(path_str):
    """
    Very simple dynamic import:
    e.g. path_str = 'myapp.plugins.transforms.capitalize_value'
    """
    import importlib
    module_path, func_name = path_str.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, func_name)
