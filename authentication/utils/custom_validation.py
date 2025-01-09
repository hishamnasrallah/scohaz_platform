# utils/custom_validation.py

def my_custom_validator(value, param_a=None, param_b=None):
    """
    Example: check that value is at least param_a in length, or something
    """
    if param_a is not None and len(value) < param_a:
        raise ValueError(f"Value must be at least {param_a} chars long.")

def another_validator(value, threshold=10):
    if float(value) < threshold:
        raise ValueError(f"Value must be >= {threshold}.")
