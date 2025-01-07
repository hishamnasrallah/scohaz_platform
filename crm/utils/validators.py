
import re
from datetime import datetime
from django.core.exceptions import ValidationError

# Registry to map rule types to validation functions
VALIDATOR_REGISTRY = {}

# Decorator to register a validation function in the registry
def register_validator(rule_type):
    def decorator(func):
        VALIDATOR_REGISTRY[rule_type] = func
        return func
    return decorator

# Base Validation Utilities
@register_validator('regex')
def validate_regex(value, pattern, error_message="Invalid format", **kwargs):
    if not re.match(pattern, str(value)):
        raise ValidationError(error_message)

@register_validator('custom')
def validate_custom_function(value, function_path, error_message="Custom validation failed", instance=None, user=None, **kwargs):
    module_path, func_name = function_path.rsplit('.', 1)
    try:
        module = __import__(module_path, fromlist=[func_name])
        func = getattr(module, func_name)
        func(value, instance=instance, user=user)
    except Exception as e:
        raise ValidationError(f"{error_message}: {str(e)}")

@register_validator('range')
def validate_range(value, min_value, max_value, error_message="Value out of range", **kwargs):
    if value < min_value or value > max_value:
        raise ValidationError(error_message)

@register_validator('choice')
def validate_choice(value, choices, error_message="Invalid choice", **kwargs):
    if value not in choices:
        raise ValidationError(error_message)


@register_validator('priority')
def validate_priority(value, error_message="Priority must be one of: medium, or high", **kwargs):
    """
    Custom validator to ensure the priority is one of the allowed values.
    """
    allowed_priorities = ['medium', 'high']

    # Check if the value is in the allowed priorities
    if value not in allowed_priorities:
        raise ValidationError(error_message)

@register_validator('company_name')
def validate_company_name(value, error_message="Invalid company_name", **kwargs):
    if is_string_number(value):
        raise ValidationError(error_message)

def is_string_number(var):
    """
    Determines if the given variable is a string that represents a number.

    Parameters:
    var (any): The variable to check.

    Returns:
    tuple: (bool, str) where bool indicates if var is a numeric string,
           and str provides a descriptive message.
    """
    # 1. Type Check
    if not isinstance(var, str):
        return False, "Variable is not a string."

    # 2. Whitespace Handling
    stripped_var = var.strip()

    # 3. Empty String Check
    if not stripped_var:
        return False, "String is empty or only contains whitespace."

    # 4. Special Value Handling
    special_values = {"nan", "infinity", "-infinity", "inf", "-inf"}
    if stripped_var.lower() in special_values:
        return True, "Special floating-point value."

    # 5. Numeric Conversion
    try:
        int_value = int(stripped_var)
        return True, "Integer."
    except ValueError:
        pass

    try:
        float_value = float(stripped_var)
        return True, "Float."
    except ValueError:
        pass

    # 6. Final Validation
    return False
