from django.urls import path, include
from rest_framework.routers import DefaultRouter

from reporting.apis.views import (
    ReportViewSet, ReportDataSourceViewSet, ReportFieldViewSet,
    ReportFilterViewSet, ReportJoinViewSet, ReportParameterViewSet,
    ReportExecutionViewSet, ReportScheduleViewSet, SavedReportResultViewSet,
    FieldLookupView, ModelFieldsView, AvailableContentTypesView, ContentTypeFieldsView, TimezoneChoicesView,
    ReportingFieldTypeViewSet
)

app_name = 'reporting'

# Create router
router = DefaultRouter()
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'data-sources', ReportDataSourceViewSet, basename='datasource')
router.register(r'fields', ReportFieldViewSet, basename='field')
router.register(r'filters', ReportFilterViewSet, basename='filter')
router.register(r'joins', ReportJoinViewSet, basename='join')
router.register(r'parameters', ReportParameterViewSet, basename='parameter')
router.register(r'executions', ReportExecutionViewSet, basename='execution')
router.register(r'schedules', ReportScheduleViewSet, basename='schedule')
router.register(r'saved-results', SavedReportResultViewSet, basename='savedresult')
router.register(r'field-types', ReportingFieldTypeViewSet, basename='fieldtype')


urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),

    # Utility endpoints
    path('api/field-lookups/', FieldLookupView.as_view(), name='field-lookups'),
    path('api/model-fields/', ModelFieldsView.as_view(), name='model-fields'),

    # New dropdown support endpoints
    path('api/content-types/', AvailableContentTypesView.as_view(), name='available-content-types'),
    path('api/content-type-fields/', ContentTypeFieldsView.as_view(), name='content-type-fields'),
    path('api/timezone-choices/', TimezoneChoicesView.as_view(), name='timezone-choices'),
]