from django.urls import path, include
from rest_framework.routers import DefaultRouter
from crm.views import IntegrationConfigViewSet, ValidationRuleViewSet, CustomerViewSet, LeadViewSet, ActivityViewSet, ProductViewSet, InvoiceViewSet, PaymentViewSet


router = DefaultRouter()
router.register(r'integration-configs', IntegrationConfigViewSet)
router.register(r'validation-rules', ValidationRuleViewSet)
router.register(r'customer', CustomerViewSet)
router.register(r'lead', LeadViewSet)
router.register(r'activity', ActivityViewSet)
router.register(r'product', ProductViewSet)
router.register(r'invoice', InvoiceViewSet)
router.register(r'payment', PaymentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
