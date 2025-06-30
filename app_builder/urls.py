from django.urls import path, include

from app_builder import views
from app_builder.views import ApplicationDefinitionViewSet, ModelDefinitionViewSet, FieldDefinitionViewSet, \
    RelationshipDefinitionViewSet, DiagramImportView, ApplicationDefinitionERDView

app_name = 'app_builder'  # This defines the namespace
from rest_framework.routers import DefaultRouter

urlpatterns = [
    # path('', views.list_applications, name='list_applications'),
    # path('create/', views.application_definition_crud, name='create_application'),
    # path('<int:pk>/edit/', views.application_definition_crud, name='edit_application'),
    # path('<int:pk>/delete/', views.delete_application, name='delete_application'),
]



router = DefaultRouter()
router.register(r'applications', ApplicationDefinitionViewSet, basename='applicationdefinition')
router.register(r'models', ModelDefinitionViewSet, basename='modeldefinition')
router.register(r'fields', FieldDefinitionViewSet, basename='fielddefinition')
router.register(r'relationships', RelationshipDefinitionViewSet, basename='relationshipdefinition')

urlpatterns += [
    path('api/applications/erd/', ApplicationDefinitionERDView.as_view(), name='diagram-import-to-erd-designer'),

    path('api/', include(router.urls)),
    path('api/diagram/import/', DiagramImportView.as_view(), name='diagram-import'),

]
urlpatterns += [
    path('api/compile-create/', views.compile_and_create_app_api, name='compile-create-api'),
    path('api/compile-only/', views.compile_only_api, name='compile-only-api'),
    path('api/job-status/<str:job_id>/', views.check_job_status_api, name='job-status-api'),
]