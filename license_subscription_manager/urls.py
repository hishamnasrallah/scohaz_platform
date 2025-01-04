from django.urls import path
from license_subscription_manager.apis.views import (ValidateLicenseView,
                                                     SubscriptionManagementView)

urlpatterns = [
    path('validate_license/',
         ValidateLicenseView.as_view(), name='validate_license'),
    path('manage_subscription/',
         SubscriptionManagementView.as_view(), name='manage_subscription'),
]
