# filters.py
import django_filters
from django.db.models import Q
from dynamicflow.models import Field, Page, Category, Condition, FieldType


class FieldFilter(django_filters.FilterSet):
    """Advanced filtering for Field model"""

    # Text searches
    name = django_filters.CharFilter(field_name='_field_name', lookup_expr='icontains')
    display_name = django_filters.CharFilter(field_name='_field_display_name', lookup_expr='icontains')

    # Multiple choice filters
    services = django_filters.ModelMultipleChoiceFilter(
        field_name='service',
        queryset=None,  # Will be set in __init__
        conjoined=False  # OR logic for multiple services
    )
    categories = django_filters.ModelMultipleChoiceFilter(
        field_name='_category',
        queryset=None,  # Will be set in __init__
        conjoined=False
    )
    field_types = django_filters.ModelMultipleChoiceFilter(
        field_name='_field_type',
        queryset=FieldType.objects.all(),
        conjoined=False
    )

    # Range filters
    sequence_min = django_filters.NumberFilter(field_name='_sequence', lookup_expr='gte')
    sequence_max = django_filters.NumberFilter(field_name='_sequence', lookup_expr='lte')

    # Boolean filters
    has_parent = django_filters.BooleanFilter(
        method='filter_has_parent',
        label='Has parent field'
    )
    has_sub_fields = django_filters.BooleanFilter(
        method='filter_has_sub_fields',
        label='Has sub fields'
    )
    has_conditions = django_filters.BooleanFilter(
        method='filter_has_conditions',
        label='Has conditions'
    )

    # Validation filters
    has_regex = django_filters.BooleanFilter(
        method='filter_has_regex',
        label='Has regex validation'
    )
    is_numeric = django_filters.BooleanFilter(
        method='filter_is_numeric',
        label='Is numeric field'
    )

    class Meta:
        model = Field
        fields = {
            '_mandatory': ['exact'],
            '_is_hidden': ['exact'],
            '_is_disabled': ['exact'],
            'active_ind': ['exact'],
            '_sequence': ['exact', 'gte', 'lte'],
            '_max_length': ['exact', 'gte', 'lte'],
            '_min_length': ['exact', 'gte', 'lte'],
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set querysets for foreign key filters
        from lookup.models import Lookup  # Assuming this is the lookup app
        self.filters['services'].queryset = Lookup.objects.filter(
            parent_lookup__name='Service'
        )
        self.filters['categories'].queryset = Category.objects.filter(active_ind=True)

    def filter_has_parent(self, queryset, name, value):
        if value:
            return queryset.filter(_parent_field__isnull=False)
        return queryset.filter(_parent_field__isnull=True)

    def filter_has_sub_fields(self, queryset, name, value):
        if value:
            return queryset.filter(sub_fields__isnull=False).distinct()
        return queryset.filter(sub_fields__isnull=True)

    def filter_has_conditions(self, queryset, name, value):
        if value:
            return queryset.filter(conditions__isnull=False).distinct()
        return queryset.filter(conditions__isnull=True)

    def filter_has_regex(self, queryset, name, value):
        if value:
            return queryset.exclude(Q(_regex_pattern__isnull=True) | Q(_regex_pattern=''))
        return queryset.filter(Q(_regex_pattern__isnull=True) | Q(_regex_pattern=''))

    def filter_is_numeric(self, queryset, name, value):
        numeric_types = ['number', 'integer', 'decimal', 'float']
        if value:
            return queryset.filter(_field_type__name__in=numeric_types)
        return queryset.exclude(_field_type__name__in=numeric_types)


class PageFilter(django_filters.FilterSet):
    """Advanced filtering for Page model"""

    name = django_filters.CharFilter(lookup_expr='icontains')
    description = django_filters.CharFilter(lookup_expr='icontains')

    # Service filtering
    service_name = django_filters.CharFilter(
        field_name='service__name',
        lookup_expr='icontains'
    )

    # Date filtering (if you add created/modified dates to your models)
    # created_after = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    # created_before = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Page
        fields = {
            'service': ['exact'],
            'sequence_number': ['exact'],
            'applicant_type': ['exact'],
            'active_ind': ['exact'],
        }


class ConditionFilter(django_filters.FilterSet):
    """Advanced filtering for Condition model"""

    target_field_name = django_filters.CharFilter(
        field_name='target_field___field_name',
        lookup_expr='icontains'
    )

    # Filter by fields referenced in condition logic
    references_field = django_filters.CharFilter(
        method='filter_references_field',
        label='References field in condition logic'
    )

    # Filter by operation types used in conditions
    uses_operation = django_filters.CharFilter(
        method='filter_uses_operation',
        label='Uses specific operation'
    )

    class Meta:
        model = Condition
        fields = {
            'target_field': ['exact'],
            'active_ind': ['exact'],
        }

    def filter_references_field(self, queryset, name, value):
        """Filter conditions that reference a specific field in their logic"""
        return queryset.filter(
            condition_logic__contains=[{"field": value}]
        )

    def filter_uses_operation(self, queryset, name, value):
        """Filter conditions that use a specific operation"""
        return queryset.filter(
            condition_logic__contains=[{"operation": value}]
        )


# utils.py
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from rest_framework.response import Response
from rest_framework import status
import re
from datetime import datetime, date


class FieldValidationUtils:
    """Utility class for field validation logic"""

    @staticmethod
    def validate_text_field(field, value):
        """Validate text field against its constraints"""
        errors = []

        if not isinstance(value, str):
            value = str(value)

        # Length validation
        if field._min_length and len(value) < field._min_length:
            errors.append(f"Value must be at least {field._min_length} characters long")

        if field._max_length and len(value) > field._max_length:
            errors.append(f"Value must be at most {field._max_length} characters long")

        # Regex validation
        if field._regex_pattern and not re.match(field._regex_pattern, value):
            errors.append("Value does not match the required pattern")

        # Allowed characters validation
        if field._allowed_characters:
            allowed_chars = set(field._allowed_characters)
            value_chars = set(value)
            if not value_chars.issubset(allowed_chars):
                invalid_chars = value_chars - allowed_chars
                errors.append(f"Contains invalid characters: {', '.join(invalid_chars)}")

        # Forbidden words validation
        if field._forbidden_words:
            forbidden_words = [word.strip() for word in field._forbidden_words.split(',')]
            value_lower = value.lower()
            for word in forbidden_words:
                if word.lower() in value_lower:
                    errors.append(f"Contains forbidden word: {word}")

        return errors

    @staticmethod
    def validate_number_field(field, value):
        """Validate numeric field against its constraints"""
        errors = []

        try:
            num_value = float(value)
        except (ValueError, TypeError):
            return ["Value must be a valid number"]

        # Integer only validation
        if field._integer_only and not num_value.is_integer():
            errors.append("Value must be an integer")

        # Positive only validation
        if field._positive_only and num_value <= 0:
            errors.append("Value must be positive")

        # Range validation
        if field._value_greater_than is not None and num_value <= field._value_greater_than:
            errors.append(f"Value must be greater than {field._value_greater_than}")

        if field._value_less_than is not None and num_value >= field._value_less_than:
            errors.append(f"Value must be less than {field._value_less_than}")

        return errors

    @staticmethod
    def validate_date_field(field, value):
        """Validate date field against its constraints"""
        errors = []

        if isinstance(value, str):
            try:
                # Try to parse common date formats
                for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
                    try:
                        date_value = datetime.strptime(value, fmt).date()
                        break
                    except ValueError:
                        continue
                else:
                    return ["Invalid date format"]
            except ValueError:
                return ["Invalid date format"]
        elif isinstance(value, date):
            date_value = value
        else:
            return ["Value must be a valid date"]

        # Future only validation
        if field._future_only and date_value <= date.today():
            errors.append("Date must be in the future")

        # Past only validation
        if field._past_only and date_value >= date.today():
            errors.append("Date must be in the past")

        # Date range validation
        if field._date_greater_than and date_value <= field._date_greater_than:
            errors.append(f"Date must be after {field._date_greater_than}")

        if field._date_less_than and date_value >= field._date_less_than:
            errors.append(f"Date must be before {field._date_less_than}")

        return errors


class FormDataProcessor:
    """Utility class for processing form data and evaluating conditions"""

    @staticmethod
    def process_form_submission(page_id, form_data):
        """Process a complete form submission for a page"""
        try:
            from dynamicflow.models import Page, Field, Condition

            page = Page.objects.get(id=page_id)

            # Get all fields for this page
            fields = Field.objects.filter(
                _category__page=page,
                active_ind=True
            ).select_related('_field_type')

            # Get all conditions for these fields
            conditions = Condition.objects.filter(
                target_field__in=fields,
                active_ind=True
            )

            # Validate each field
            validation_errors = {}
            for field in fields:
                field_value = form_data.get(field._field_name)

                # Skip validation for hidden or disabled fields
                if field._is_hidden or field._is_disabled:
                    continue

                # Check if mandatory field is provided
                if field._mandatory and (field_value is None or field_value == ''):
                    validation_errors[field._field_name] = ["This field is required"]
                    continue

                # Skip validation if field is empty and not mandatory
                if field_value is None or field_value == '':
                    continue

                # Validate based on field type
                field_errors = []
                if field._field_type.name.lower() in ['text', 'textarea', 'email', 'url']:
                    field_errors = FieldValidationUtils.validate_text_field(field, field_value)
                elif field._field_type.name.lower() in ['number', 'integer', 'decimal']:
                    field_errors = FieldValidationUtils.validate_number_field(field, field_value)
                elif field._field_type.name.lower() in ['date', 'datetime']:
                    field_errors = FieldValidationUtils.validate_date_field(field, field_value)

                if field_errors:
                    validation_errors[field._field_name] = field_errors

            # Evaluate conditions to determine visible fields
            visible_fields = []
            for condition in conditions:
                try:
                    if condition.evaluate_condition(form_data):
                        visible_fields.append(condition.target_field._field_name)
                except Exception as e:
                    # Log condition evaluation error but don't fail the entire process
                    pass

            return {
                'page_id': page_id,
                'validation_errors': validation_errors,
                'visible_fields': visible_fields,
                'is_valid': len(validation_errors) == 0,
                'processed_fields': [field._field_name for field in fields]
            }

        except Page.DoesNotExist:
            return {
                'error': f'Page with id {page_id} does not exist',
                'is_valid': False
            }
        except Exception as e:
            return {
                'error': f'Error processing form: {str(e)}',
                'is_valid': False
            }

    @staticmethod
    def get_form_schema(page_id):
        """Get the complete form schema for a page including conditions"""
        try:
            from dynamicflow.models import Page, Field, Condition

            page = Page.objects.get(id=page_id)

            # Get all categories for this page
            categories = page.category_set.filter(active_ind=True).order_by('name')

            schema = {
                'page': {
                    'id': page.id,
                    'name': page.name,
                    'name_ara': page.name_ara,
                    'description': page.description,
                    'description_ara': page.description_ara
                },
                'categories': []
            }

            for category in categories:
                # Get fields for this category
                fields = category.field_set.filter(
                    active_ind=True,
                    _parent_field__isnull=True  # Only root fields
                ).order_by('_sequence')

                category_data = {
                    'id': category.id,
                    'name': category.name,
                    'name_ara': category.name_ara,
                    'is_repeatable': category.is_repeatable,
                    'fields': []
                }

                for field in fields:
                    field_data = {
                        'id': field.id,
                        'name': field._field_name,
                        'display_name': field._field_display_name,
                        'display_name_ara': field._field_display_name_ara,
                        'type': field._field_type.name if field._field_type else None,
                        'mandatory': field._mandatory,
                        'hidden': field._is_hidden,
                        'disabled': field._is_disabled,
                        'sequence': field._sequence,
                        'validation': {
                            'max_length': field._max_length,
                            'min_length': field._min_length,
                            'regex_pattern': field._regex_pattern,
                            'allowed_characters': field._allowed_characters,
                            'value_greater_than': field._value_greater_than,
                            'value_less_than': field._value_less_than,
                            'integer_only': field._integer_only,
                            'positive_only': field._positive_only,
                            'date_greater_than': field._date_greater_than,
                            'date_less_than': field._date_less_than,
                            'future_only': field._future_only,
                            'past_only': field._past_only,
                        },
                        'sub_fields': [],
                        'conditions': []
                    }

                    # Add sub-fields recursively
                    def add_sub_fields(parent_field, parent_data):
                        sub_fields = parent_field.sub_fields.filter(active_ind=True).order_by('_sequence')
                        for sub_field in sub_fields:
                            sub_field_data = {
                                'id': sub_field.id,
                                'name': sub_field._field_name,
                                'display_name': sub_field._field_display_name,
                                'type': sub_field._field_type.name if sub_field._field_type else None,
                                'mandatory': sub_field._mandatory,
                                'sequence': sub_field._sequence,
                                'sub_fields': []
                            }
                            add_sub_fields(sub_field, sub_field_data)
                            parent_data['sub_fields'].append(sub_field_data)

                    add_sub_fields(field, field_data)

                    # Add conditions for this field
                    conditions = field.conditions.filter(active_ind=True)
                    for condition in conditions:
                        field_data['conditions'].append({
                            'id': condition.id,
                            'logic': condition.condition_logic
                        })

                    category_data['fields'].append(field_data)

                schema['categories'].append(category_data)

            return schema

        except Page.DoesNotExist:
            return {'error': f'Page with id {page_id} does not exist'}
        except Exception as e:
            return {'error': f'Error generating schema: {str(e)}'}


# Custom API response helpers
def api_response(data=None, message=None, status_code=status.HTTP_200_OK, errors=None):
    """Standardized API response format"""
    response_data = {}

    if data is not None:
        response_data['data'] = data

    if message:
        response_data['message'] = message

    if errors:
        response_data['errors'] = errors

    response_data['success'] = status_code < 400

    return Response(response_data, status=status_code)


def paginated_response(serializer, message=None):
    """Helper for paginated responses"""
    return api_response(
        data={
            'results': serializer.data,
            'count': serializer.instance.count() if hasattr(serializer.instance, 'count') else len(serializer.data),
        },
        message=message
    )