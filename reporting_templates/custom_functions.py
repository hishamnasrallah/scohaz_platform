# reporting_templates/custom_functions.py

"""
Example custom functions for PDF template data fetching and transformation.
These functions can be referenced in template configurations.
"""

from datetime import datetime, timedelta
from django.db.models import Q, Count, Sum, Avg
from django.contrib.auth import get_user_model
from case.models import Case
from lookup.models import Lookup

User = get_user_model()


# Data Fetching Functions
# These functions are called with (user, parameters, template) arguments

def fetch_user_cases_summary(user, parameters, template):
    """
    Fetch summary of user's cases grouped by status.
    Can be used as custom_function_path in PDFTemplate.
    """
    # Get date range from parameters
    start_date = parameters.get('start_date')
    end_date = parameters.get('end_date')

    # Base query
    cases = Case.objects.filter(applicant=user)

    # Apply date filter if provided
    if start_date:
        cases = cases.filter(created_at__gte=start_date)
    if end_date:
        cases = cases.filter(created_at__lte=end_date)

    # Get summary
    summary = cases.values('status__name').annotate(
        count=Count('id')
    ).order_by('status__name')

    # Get total
    total = cases.count()

    return {
        'summary': list(summary),
        'total': total,
        'date_range': {
            'start': start_date or 'All time',
            'end': end_date or 'Present'
        }
    }


def fetch_employee_report_data(user, parameters, template):
    """
    Fetch data for employee reports - can see other users' data.
    """
    # Check if user has permission
    if not user.has_perm('reporting_templates.can_generate_others_pdf'):
        raise PermissionError("User doesn't have permission to generate reports for others")

    # Get target user
    target_user_id = parameters.get('user_id')
    if not target_user_id:
        raise ValueError("user_id parameter is required")

    try:
        target_user = User.objects.get(id=target_user_id)
    except User.DoesNotExist:
        raise ValueError("Target user not found")

    # Fetch cases for target user
    cases = Case.objects.filter(
        applicant=target_user
    ).select_related('status', 'case_type')

    # Apply additional filters
    if parameters.get('case_type'):
        cases = cases.filter(case_type__code=parameters['case_type'])

    if parameters.get('status'):
        cases = cases.filter(status__code=parameters['status'])

    return {
        'target_user': target_user,
        'cases': cases,
        'total_cases': cases.count(),
        'report_generated_by': user,
        'report_date': datetime.now()
    }


def fetch_department_statistics(user, parameters, template):
    """
    Fetch department-wide statistics.
    """
    # Get department from parameters or user's groups
    department = parameters.get('department')
    if not department:
        # Use first group as department
        department = user.groups.first()

    # Get all users in department
    department_users = User.objects.filter(groups=department)

    # Get statistics
    stats = {
        'department': department,
        'total_users': department_users.count(),
        'total_cases': Case.objects.filter(
            assigned_group=department
        ).count(),
        'pending_cases': Case.objects.filter(
            assigned_group=department,
            status__name='Pending'
        ).count(),
        'completed_cases': Case.objects.filter(
            assigned_group=department,
            status__name='Completed'
        ).count(),
        'average_completion_time': None  # Calculate if needed
    }

    return stats


# Data Source Functions
# These are called with (user, parameters, context, data_source) arguments

def fetch_related_documents(user, parameters, context, data_source):
    """
    Fetch documents related to a case.
    Used as custom_function_path in PDFTemplateDataSource.
    """
    # Get case from context
    case = context.get('main')
    if not case or not hasattr(case, 'case_data'):
        return []

    # Extract document information from case_data
    documents = []
    case_data = case.case_data or {}

    if 'uploaded_files' in case_data:
        for file_info in case_data['uploaded_files']:
            documents.append({
                'type': file_info.get('type', 'Unknown'),
                'url': file_info.get('file_url', ''),
                'uploaded_date': case.created_at
            })

    return documents


def fetch_approval_history(user, parameters, context, data_source):
    """
    Fetch approval history for a case.
    """
    case = context.get('main')
    if not case:
        return []

    # Get approval records
    approvals = []

    # This is a simplified example - adjust based on your actual models
    # You might have an ApprovalRecord model or similar
    if hasattr(case, 'approval_records'):
        for record in case.approval_records.all():
            approvals.append({
                'step': record.approval_step.name,
                'approved_by': record.approved_by.get_full_name(),
                'approved_at': record.approved_at,
                'comments': getattr(record, 'comments', '')
            })

    return approvals


# Transform Functions
# These are called with (value, context) arguments

def format_currency(value, context=None):
    """
    Format number as currency.
    Used as transform_function in PDFTemplateVariable.
    """
    if value is None:
        return '0.00'

    # Get currency from context if available
    currency = 'JOD'  # Default currency
    if context and 'currency' in context:
        currency = context['currency']

    return f"{currency} {value:,.2f}"


def format_percentage(value, context=None):
    """
    Format number as percentage.
    """
    if value is None:
        return '0%'

    return f"{value:.1%}"


def translate_status(value, context=None):
    """
    Translate status code to display name.
    """
    if not value:
        return 'Unknown'

    # If it's already a Lookup object
    if hasattr(value, 'name'):
        return value.name

    # Try to find the lookup
    try:
        lookup = Lookup.objects.get(
            parent_lookup__name='Case Status',
            code=value
        )
        return lookup.name
    except Lookup.DoesNotExist:
        return value


def calculate_age(value, context=None):
    """
    Calculate age from birth date.
    """
    if not value:
        return 'N/A'

    if isinstance(value, str):
        value = datetime.strptime(value, '%Y-%m-%d').date()

    today = datetime.now().date()
    age = today.year - value.year

    # Adjust if birthday hasn't occurred this year
    if today.month < value.month or (today.month == value.month and today.day < value.day):
        age -= 1

    return str(age)


def mask_sensitive_data(value, context=None):
    """
    Mask sensitive data like phone numbers or IDs.
    """
    if not value:
        return ''

    value_str = str(value)

    # Keep first 2 and last 2 characters
    if len(value_str) > 4:
        masked = value_str[:2] + '*' * (len(value_str) - 4) + value_str[-2:]
    else:
        masked = '*' * len(value_str)

    return masked


# Post-processing Functions
# These are called with (data, context) arguments

def sort_by_date(data, context=None):
    """
    Sort list of items by date field.
    """
    if not isinstance(data, list):
        return data

    # Try common date field names
    date_fields = ['created_at', 'date', 'timestamp', 'approved_at']

    for field in date_fields:
        if data and field in data[0]:
            return sorted(data, key=lambda x: x.get(field), reverse=True)

    return data


def group_by_category(data, context=None):
    """
    Group items by category.
    """
    if not isinstance(data, list):
        return data

    grouped = {}

    for item in data:
        category = item.get('category', 'Other')
        if category not in grouped:
            grouped[category] = []
        grouped[category].append(item)

    return grouped


def calculate_totals(data, context=None):
    """
    Calculate totals for numeric fields.
    """
    if not isinstance(data, list) or not data:
        return {'items': data, 'totals': {}}

    totals = {}

    # Find numeric fields
    first_item = data[0]
    for key, value in first_item.items():
        if isinstance(value, (int, float)):
            totals[key] = sum(item.get(key, 0) for item in data)

    return {
        'items': data,
        'totals': totals,
        'count': len(data)
    }