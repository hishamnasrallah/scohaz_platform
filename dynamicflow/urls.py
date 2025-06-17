# urls.py
from dynamicflow.apis.additional_views import FormSchemaAPIView, FormSubmissionAPIView, FormExportAPIView, \
    FormImportAPIView, FormStatisticsAPIView, FieldValidationAPIView
from dynamicflow.apis.views import FlowAPIView
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.documentation import include_docs_urls
from dynamicflow.apis.views import (
    FieldTypeViewSet, PageViewSet, CategoryViewSet,
    FieldViewSet, ConditionViewSet
)
urlpatterns = [

    path('service_flow/', FlowAPIView.as_view(),
         name='services_flow'),

]



# Create router and register viewsets
router = DefaultRouter()
router.register(r'field-types', FieldTypeViewSet, basename='fieldtype')
router.register(r'pages', PageViewSet, basename='page')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'fields', FieldViewSet, basename='field')
router.register(r'conditions', ConditionViewSet, basename='condition')

app_name = 'form_api'

# urlpatterns += [
#     # Main API routes
#     path('api/v1/', include(router.urls)),
#
#     # Additional API endpoints from additional_views.py
#     path('api/v1/forms/<int:page_id>/schema/', FormSchemaAPIView.as_view(), name='form-schema'),
#     path('api/v1/forms/<int:page_id>/submit/', FormSubmissionAPIView.as_view(), name='form-submit'),
#     path('api/v1/forms/<int:page_id>/export/', FormExportAPIView.as_view(), name='form-export'),
#     path('api/v1/forms/import/', FormImportAPIView.as_view(), name='form-import'),
#     path('api/v1/forms/statistics/', FormStatisticsAPIView.as_view(), name='form-statistics'),
#
#     # Field validation endpoint
#     path('api/v1/fields/<int:field_id>/validate/', FieldValidationAPIView.as_view(), name='field-validate'),
#
#     # API documentation
#     path('api/docs/', include_docs_urls(title='Form Builder API')),
#
#     # Authentication
#     path('api-auth/', include('rest_framework.urls')),
# ]

"""
API Endpoints Overview:

FIELD TYPES:
- GET    /api/v1/field-types/                    # List all field types
- POST   /api/v1/field-types/                    # Create new field type
- GET    /api/v1/field-types/{id}/               # Get specific field type
- PUT    /api/v1/field-types/{id}/               # Update field type
- PATCH  /api/v1/field-types/{id}/               # Partial update field type
- DELETE /api/v1/field-types/{id}/               # Delete field type
- GET    /api/v1/field-types/active/             # Get only active field types

PAGES:
- GET    /api/v1/pages/                          # List all pages
- POST   /api/v1/pages/                          # Create new page
- GET    /api/v1/pages/{id}/                     # Get specific page
- PUT    /api/v1/pages/{id}/                     # Update page
- PATCH  /api/v1/pages/{id}/                     # Partial update page
- DELETE /api/v1/pages/{id}/                     # Delete page
- GET    /api/v1/pages/{id}/with_fields/         # Get page with all fields
- GET    /api/v1/pages/by_service/               # Get pages by service (?service_id=X)
- POST   /api/v1/pages/{id}/duplicate/           # Duplicate a page

CATEGORIES:
- GET    /api/v1/categories/                     # List all categories
- POST   /api/v1/categories/                     # Create new category
- GET    /api/v1/categories/{id}/                # Get specific category
- PUT    /api/v1/categories/{id}/                # Update category
- PATCH  /api/v1/categories/{id}/                # Partial update category
- DELETE /api/v1/categories/{id}/                # Delete category
- GET    /api/v1/categories/repeatable/          # Get only repeatable categories
- POST   /api/v1/categories/{id}/add_pages/      # Add pages to category
- POST   /api/v1/categories/{id}/remove_pages/   # Remove pages from category

FIELDS:
- GET    /api/v1/fields/                         # List all fields
- POST   /api/v1/fields/                         # Create new field
- GET    /api/v1/fields/{id}/                    # Get specific field
- PUT    /api/v1/fields/{id}/                    # Update field
- PATCH  /api/v1/fields/{id}/                    # Partial update field
- DELETE /api/v1/fields/{id}/                    # Delete field
- GET    /api/v1/fields/{id}/with_sub_fields/    # Get field with sub-fields
- GET    /api/v1/fields/tree_structure/          # Get field tree structure
- POST   /api/v1/fields/{id}/add_sub_field/      # Add sub-field to field
- GET    /api/v1/fields/{id}/validate_field/     # Validate field value (?value=X)
- POST   /api/v1/fields/bulk_update/             # Bulk update fields
- POST   /api/v1/fields/{id}/duplicate/          # Duplicate a field
- POST   /api/v1/fields/{id}/validate/           # Individual field validation

CONDITIONS:
- GET    /api/v1/conditions/                     # List all conditions
- POST   /api/v1/conditions/                     # Create new condition
- GET    /api/v1/conditions/{id}/                # Get specific condition
- PUT    /api/v1/conditions/{id}/                # Update condition
- PATCH  /api/v1/conditions/{id}/                # Partial update condition
- DELETE /api/v1/conditions/{id}/                # Delete condition
- POST   /api/v1/conditions/{id}/test_condition/ # Test condition with data
- POST   /api/v1/conditions/evaluate_multiple/   # Evaluate multiple conditions
- GET    /api/v1/conditions/by_field/            # Get conditions by field (?field_id=X)

FORM PROCESSING (from additional_views):
- GET    /api/v1/forms/{page_id}/schema/         # Get complete form schema
- POST   /api/v1/forms/{page_id}/submit/         # Submit and validate form data  
- GET    /api/v1/forms/{page_id}/export/         # Export form configuration
- POST   /api/v1/forms/import/                   # Import form configuration
- GET    /api/v1/forms/statistics/               # Get form statistics and analytics

QUERY PARAMETERS:
Most list endpoints support:
- ?search=<term>                    # Search across relevant fields
- ?ordering=<field>                 # Order by field (prefix with - for desc)
- ?active_ind=true/false           # Filter by active status
- ?page=<num>&page_size=<size>     # Pagination

FIELD-SPECIFIC QUERY PARAMETERS:
- ?service=<id>                    # Filter fields by service
- ?category=<id>                   # Filter fields by category
- ?field_type=<name>               # Filter fields by type
- ?root_only=true                  # Get only root fields (no parent)

BULK OPERATIONS:
Fields bulk update payload:
{
    "field_ids": [1, 2, 3],
    "action": "activate|deactivate|hide|show"
}

CONDITION TESTING:
Test condition payload:
{
    "field_data": {
        "field_name": "value",
        "another_field": 123
    }
}

Evaluate multiple conditions payload:
{
    "condition_ids": [1, 2, 3],
    "field_data": {
        "field_name": "value",
        "another_field": 123
    }
}

FORM SUBMISSION:
Submit form payload:
{
    "form_data": {
        "first_name": "John",
        "last_name": "Doe", 
        "age": 30,
        "email": "john@example.com"
    }
}

FORM IMPORT:
Import form configuration payload:
{
    "form_config": {
        "page": {...},
        "categories": [...],
        "fields": [...],
        "conditions": [...]
    }
}
"""