
# Sample Filter Function

def only_if_age_above_5(item, case):
    """
    Skip children younger than 6.
    Usage in MapperTarget:
    myapp.plugins.filters.only_if_age_above_5
    """
    return item.get("age", 0) >= 6
