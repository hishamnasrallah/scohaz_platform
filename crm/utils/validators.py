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


@register_validator('min_length')
def validate_min_length(value, min_length, error_message="Value is too short", **kwargs):
    if len(str(value)) < min_length:
        raise ValidationError(error_message)


@register_validator('max_length')
def validate_max_length(value, max_length, error_message="Value is too long", **kwargs):
    if len(str(value)) > max_length:
        raise ValidationError(error_message)


@register_validator('range')
def validate_range(value, min_value=None, max_value=None, error_message="Value out of range", **kwargs):
    if min_value is not None and value < min_value:
        raise ValidationError(f"Value must be greater than or equal to {min_value}")
    if max_value is not None and value > max_value:
        raise ValidationError(f"Value must be less than or equal to {max_value}")


@register_validator('due_date')
def validate_due_date(value, instance=None, error_message="Invalid due date", **kwargs):
    """
    Validates that the due date is not before the issue date.
    """
    from crm.models import Invoice

    if instance is None:
        raise ValidationError("Instance is required for this validation.")

    # Access another field value from the instance
    status = getattr(instance, 'status', None)
    _today = datetime.now().date()

    if value is None:
        raise ValidationError("Issue date is required for this validation.")

    if value is not None and value < _today and status == 'issued':
        raise ValidationError(f"The due date cannot be before the now when status is issued.")


@register_validator('discount_range')
def validate_discount_range(value, min_value=0, max_value=100, error_message="Value out of range", **kwargs):
    if value is None or (value < min_value or value > max_value):
        raise ValidationError(f"Value must be greater than or equal to {min_value}")
    # if max_value is not None and value > max_value:
    #     raise ValidationError(f"Value must be less than or equal to {max_value}")


@register_validator('date_format')
def validate_date_format(value, date_format, error_message="Invalid date format", **kwargs):
    try:
        datetime.strptime(value, date_format)
    except ValueError:
        raise ValidationError(error_message)


@register_validator('email')
def validate_email(value, error_message="Invalid email format", **kwargs):
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    validate_regex(value, pattern, error_message)


@register_validator('phone')
def validate_phone_number(value, error_message="Invalid phone number", **kwargs):
    pattern = r'^\+?1?\d{9,15}$'
    validate_regex(value, pattern, error_message)


@register_validator('choice')
def validate_choice(value, choices, error_message="Invalid choice", **kwargs):
    if value not in choices:
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


@register_validator('is_active_permission')
def validate_is_active_permission(value, instance=None, user=None, error_message="Only Admins can set a customer as active"):
    """
    Ensures that only users in the 'Admin' group can set is_active=True.
    """
    if value and user:
        # Check if the user belongs to the 'Admin' group
        if not user.groups.filter(name='Admin').exists():
            raise ValidationError(error_message)

# Auto-register all defined validation functions
VALIDATOR_REGISTRY.update({
    name.split("validate_", 1)[-1]: func
    for name, func in list(globals().items())
    if callable(func) and name.startswith("validate_")
})
