# additional_views.py
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from dynamicflow.models import Page, Field
from .filters import FormDataProcessor, api_response
from .serializers import FieldDetailSerializer
from ..models import Condition


class FormSchemaAPIView(views.APIView):
    """API endpoint to get complete form schema for a page"""
    permission_classes = [IsAuthenticated]

    def get(self, request, page_id):
        """Get form schema for a specific page"""
        schema = FormDataProcessor.get_form_schema(page_id)

        if 'error' in schema:
            return api_response(
                errors=schema,
                status_code=status.HTTP_404_NOT_FOUND
            )

        return api_response(
            data=schema,
            message="Form schema retrieved successfully"
        )


class FormSubmissionAPIView(views.APIView):
    """API endpoint for form submission and validation"""
    permission_classes = [IsAuthenticated]

    def post(self, request, page_id):
        """Submit and validate form data for a specific page"""
        form_data = request.data.get('form_data', {})

        if not form_data:
            return api_response(
                errors={'form_data': 'Form data is required'},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        result = FormDataProcessor.process_form_submission(page_id, form_data)

        if 'error' in result:
            return api_response(
                errors=result,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if result['is_valid']:
            return api_response(
                data=result,
                message="Form submission is valid"
            )
        else:
            return api_response(
                data=result,
                message="Form submission has validation errors",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
            )


class FieldValidationAPIView(views.APIView):
    """API endpoint for individual field validation"""
    permission_classes = [IsAuthenticated]

    def post(self, request, field_id):
        """Validate a single field value"""
        field = get_object_or_404(Field, id=field_id)
        value = request.data.get('value')

        if value is None:
            return api_response(
                errors={'value': 'Value is required'},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        from .filters import FieldValidationUtils

        # Determine field type and validate accordingly
        field_type = field._field_type.name.lower() if field._field_type else 'text'

        errors = []
        if field_type in ['text', 'textarea', 'email', 'url']:
            errors = FieldValidationUtils.validate_text_field(field, value)
        elif field_type in ['number', 'integer', 'decimal']:
            errors = FieldValidationUtils.validate_number_field(field, value)
        elif field_type in ['date', 'datetime']:
            errors = FieldValidationUtils.validate_date_field(field, value)

        result = {
            'field_id': field_id,
            'field_name': field._field_name,
            'value': value,
            'is_valid': len(errors) == 0,
            'errors': errors
        }

        return api_response(
            data=result,
            message="Field validation completed"
        )


class FormStatisticsAPIView(views.APIView):
    """API endpoint for form statistics and analytics"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get statistics about forms, fields, and conditions"""
        from django.db.models import Count
        from dynamicflow.models import Page, Category, Field, Condition, FieldType

        stats = {
            'pages': {
                'total': Page.objects.count(),
                'active': Page.objects.filter(active_ind=True).count(),
                'by_service': list(
                    Page.objects.filter(active_ind=True)
                    .values('service__name')
                    .annotate(count=Count('id'))
                    .order_by('-count')
                )
            },
            'categories': {
                'total': Category.objects.count(),
                'active': Category.objects.filter(active_ind=True).count(),
                'repeatable': Category.objects.filter(is_repeatable=True, active_ind=True).count(),
            },
            'fields': {
                'total': Field.objects.count(),
                'active': Field.objects.filter(active_ind=True).count(),
                'mandatory': Field.objects.filter(_mandatory=True, active_ind=True).count(),
                'hidden': Field.objects.filter(_is_hidden=True).count(),
                'with_conditions': Field.objects.filter(conditions__isnull=False).distinct().count(),
                'by_type': list(
                    Field.objects.filter(active_ind=True)
                    .values('_field_type__name')
                    .annotate(count=Count('id'))
                    .order_by('-count')
                ),
                'root_fields': Field.objects.filter(_parent_field__isnull=True, active_ind=True).count(),
                'sub_fields': Field.objects.filter(_parent_field__isnull=False, active_ind=True).count(),
            },
            'conditions': {
                'total': Condition.objects.count(),
                'active': Condition.objects.filter(active_ind=True).count(),
            },
            'field_types': {
                'total': FieldType.objects.count(),
                'active': FieldType.objects.filter(active_ind=True).count(),
            }
        }

        return api_response(
            data=stats,
            message="Form statistics retrieved successfully"
        )


class FormExportAPIView(views.APIView):
    """API endpoint for exporting form configurations"""
    permission_classes = [IsAuthenticated]

    def get(self, request, page_id):
        """Export complete form configuration as JSON"""
        try:
            page = Page.objects.get(id=page_id)

            # Get complete form structure
            export_data = {
                'page': {
                    'name': page.name,
                    'name_ara': page.name_ara,
                    'is_review_page':page.is_review_page,
                    'description': page.description,
                    'description_ara': page.description_ara,
                    'service': page.service.name if page.service else None,
                    'sequence_number': page.sequence_number.name if page.sequence_number else None,
                    'applicant_type': page.applicant_type.name if page.applicant_type else None,
                },
                'categories': [],
                'fields': [],
                'conditions': []
            }

            # Export categories
            categories = page.category_set.filter(active_ind=True)
            for category in categories:
                export_data['categories'].append({
                    'name': category.name,
                    'name_ara': category.name_ara,
                    'code': category.code,
                    'is_repeatable': category.is_repeatable,
                    'description': category.description,
                })

            # Export fields
            fields = Field.objects.filter(
                _category__page=page,
                active_ind=True
            ).select_related('_field_type', '_parent_field')

            for field in fields:
                field_data = FieldDetailSerializer(field).data
                export_data['fields'].append(field_data)

            # Export conditions
            conditions = Condition.objects.filter(
                target_field__in=fields,
                active_ind=True
            )

            for condition in conditions:
                export_data['conditions'].append({
                    'target_field_name': condition.target_field._field_name,
                    'condition_logic': condition.condition_logic,
                })

            return api_response(
                data=export_data,
                message=f"Form configuration for page '{page.name}' exported successfully"
            )

        except Page.DoesNotExist:
            return api_response(
                errors={'page_id': f'Page with id {page_id} does not exist'},
                status_code=status.HTTP_404_NOT_FOUND
            )


class FormImportAPIView(views.APIView):
    """API endpoint for importing form configurations"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Import form configuration from JSON"""
        import_data = request.data.get('form_config')

        if not import_data:
            return api_response(
                errors={'form_config': 'Form configuration data is required'},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            # This is a simplified import process
            # In a real implementation, you'd want more robust error handling
            # and validation of the import data structure

            result = {
                'imported': {
                    'pages': 0,
                    'categories': 0,
                    'fields': 0,
                    'conditions': 0
                },
                'errors': []
            }

            # Import page (this is a basic example)
            page_data = import_data.get('page', {})
            if page_data:
                # Here you would create the page with proper lookup handling
                result['imported']['pages'] = 1

            # Import categories
            categories_data = import_data.get('categories', [])
            result['imported']['categories'] = len(categories_data)

            # Import fields
            fields_data = import_data.get('fields', [])
            result['imported']['fields'] = len(fields_data)

            # Import conditions
            conditions_data = import_data.get('conditions', [])
            result['imported']['conditions'] = len(conditions_data)

            return api_response(
                data=result,
                message="Form configuration imported successfully"
            )

        except Exception as e:
            return api_response(
                errors={'import': f'Error importing form: {str(e)}'},
                status_code=status.HTTP_400_BAD_REQUEST
            )


# Additional URLs are now integrated into the main urls.py file

# settings.py additions
"""
# Add these to your Django settings.py file:

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'EXCEPTION_HANDLER': 'your_app.exceptions.custom_exception_handler',  # Optional
}

# CORS settings (if you need to allow cross-origin requests)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React development server
    "http://127.0.0.1:3000",
    # Add your frontend URLs here
]

CORS_ALLOW_CREDENTIALS = True

# API rate limiting (optional)
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = [
    'rest_framework.throttling.AnonRateThrottle',
    'rest_framework.throttling.UserRateThrottle'
]

REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '100/hour',
    'user': '1000/hour'
}

# Cache configuration for better API performance
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'form_api',
    }
}

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'api.log',
        },
    },
    'loggers': {
        'your_app.views': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
"""