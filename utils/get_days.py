# autocompute/utils/utils.py

from datetime import timedelta
from django.utils import timezone

def get_date_days_ahead(days: int):
    """
    Returns the date 'days' days ahead from today.
    """
    return timezone.now().date() + timedelta(days=days)

def get_datetime_days_ahead(days: int):
    """
    Returns the datetime 'days' days ahead from now.
    """
    return timezone.now() + timedelta(days=days)

# Add more utility functions as needed for your action logic
