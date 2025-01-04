from django.urls import path
from integration.apis.views import CallIntegrationView

urlpatterns = [
    path('call/<int:integration_id>/',
         CallIntegrationView.as_view(), name='call_integration'),
]
