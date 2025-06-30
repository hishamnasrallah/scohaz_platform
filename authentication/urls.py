from django.urls import path, re_path, include
from rest_framework.routers import DefaultRouter
from authentication.apis.views import (
    ScohazTokenObtainPairView,
    ScohazTokenRefreshView,
    RegistrationAPIView,
    ActivateEmail,
    ResendActivationEmail,
    ActivateSMSAPIView,
    ResendActivateSMSAPIView,
    RequestResetPasswordSMS,
    NewPassword,
    ChangePasswordView,
    UserPreferenceAPIView,
    UserPhoneNumberAPIView,
    TranslationAPIView,
    CRUDPermissionViewSet,
    ContentTypeAppListView,
    ContentTypeModelListView,
    UserDetailAPIView,
    GroupViewSet,
    CustomUserViewSet  # Add this import
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'groups', GroupViewSet, basename='group')
router.register(r'crud-permissions', CRUDPermissionViewSet, basename='crudpermission')
router.register(r'customuser', CustomUserViewSet, basename='customuser')  # Add this line

urlpatterns = [
    # Include all router URLs (groups, crud-permissions, customuser)
    path('', include(router.urls)),

    # Keep all existing authentication URLs exactly as they are
    path('content-types/apps/', ContentTypeAppListView.as_view(), name='content-type-apps'),
    path('content-types/models/', ContentTypeModelListView.as_view(), name='content-type-models'),
    path('login/', ScohazTokenObtainPairView.as_view(), name='jwt_login'),
    path('register/', RegistrationAPIView.as_view(), name='register'),
    path('activate_sms/', ActivateSMSAPIView.as_view(), name='activate_sms'),
    path('resend_activation_code_sms/', ResendActivateSMSAPIView.as_view(), name='resend_activate_sms'),
    path('refresh-token/', ScohazTokenRefreshView.as_view(), name='jwt_refresh'),
    path('request_reset_sms/', RequestResetPasswordSMS.as_view()),
    path('request_password_reset/', NewPassword.as_view()),
    path('change_password/', ChangePasswordView.as_view(), name='auth_change_password'),
    re_path(
        r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/'
        r'(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        ActivateEmail.as_view(),
        name='activate'
    ),
    path('resend-activation-link/', ResendActivationEmail.as_view(), name='resend_email'),
    path('me/', UserDetailAPIView.as_view(), name='user-detail'),
    path('preferences/', UserPreferenceAPIView.as_view(), name='user_preferences'),
    path('translation/<str:language>/', TranslationAPIView.as_view(), name='get_translation'),
    path('phone_numbers/', UserPhoneNumberAPIView.as_view(), name='user-phone-numbers'),
    path('phone_numbers/<int:pk>/', UserPhoneNumberAPIView.as_view(), name='user-phone-number-detail'),
]