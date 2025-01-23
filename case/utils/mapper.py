# myapp/services.py

import importlib
from django.db import transaction
from case.models import CaseMapper, MapperTarget

def execute_mappings(case):
    """
    1. Find the CaseMapper that matches `case.case_type` (etc.).
    2. For each MapperTarget, dynamically load & call the finder + processor.
    """

    # Example: find the first matching mapper
    # In production, you might have a more complex query or multiple mappers
    try:
        mapper = CaseMapper.objects.get(case_type=case.case_type)
    except CaseMapper.DoesNotExist:
        # No mapper for this case_type => do nothing or raise
        print(f"No CaseMapper found for case_type={case.case_type}")
        return

    # We can wrap in a transaction if we want all-or-nothing
    with transaction.atomic():
        for target in mapper.targets.all():
            finder_func = load_function_by_path(
                target.finder_function_path
            ) if target.finder_function_path else load_function_by_path(
                "myapp.plugins.default_plugin.find_records"
            )
            processor_func = load_function_by_path(
                target.processor_function_path
            ) if target.processor_function_path else load_function_by_path(
                "myapp.plugins.default_plugin.process_records"
            )

            found_objects = finder_func(case, target)
            # Note that the default_plugin expects None or a single object,
            # but your advanced plugin might return a queryset or list.
            # We'll handle that below.

            # Distinguish between "single object" or "list/queryset"
            if found_objects is None:
                # Single-object scenario
                updated = processor_func(case, target, None)
            elif isinstance(found_objects, list) or hasattr(found_objects, 'exists'):
                # It's a list or queryset
                updated = processor_func(case, target, found_objects)
            else:
                # It's presumably a single object
                updated = processor_func(case, target, found_objects)

            # You might log or do something with 'updated'

def load_function_by_path(path_str):
    """
    Utility to dynamically load a function by dotted path.
    E.g. "myapp.plugins.default_plugin.find_records"
    """
    if not path_str:
        return None
    module_path, func_name = path_str.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, func_name)
