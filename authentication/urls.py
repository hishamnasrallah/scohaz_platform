from django.urls import path, re_path, include
from authentication.apis.views import (ScohazTokenObtainPairView,
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
                                       TranslationAPIView, CRUDPermissionViewSet, ContentTypeAppListView,
                                       ContentTypeModelListView, UserDetailAPIView)

from rest_framework.routers import DefaultRouter
from authentication.apis.views import GroupViewSet

router = DefaultRouter()
router.register(r'groups', GroupViewSet, basename='group')
router.register(r'crud-permissions', CRUDPermissionViewSet, basename='crudpermission')

urlpatterns = [
    path('', include(router.urls)),
]
urlpatterns += [
    path('content-types/apps/', ContentTypeAppListView.as_view(), name='content-type-apps'),
    path('content-types/models/', ContentTypeModelListView.as_view(), name='content-type-models'),
    path('login/', ScohazTokenObtainPairView.as_view(), name='jwt_login'),
    path('register/', RegistrationAPIView.as_view(), name='register'),

    path('activate_sms/', ActivateSMSAPIView.as_view(), name='activate_sms'),
    path('resend_activation_code_sms/',
         ResendActivateSMSAPIView.as_view(), name='resend_activate_sms'),
    path('refresh-token/',
         ScohazTokenRefreshView.as_view(), name='jwt_refresh'),
    path('request_reset_sms/', RequestResetPasswordSMS.as_view()),
    path('request_password_reset/', NewPassword.as_view()),
    path('change_password/',
         ChangePasswordView.as_view(), name='auth_change_password'),

    # not tested yet by email
    re_path(
        r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/'
        r'(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        ActivateEmail.as_view(),
        name='activate'
    ),
    path('resend-activation-link/',
         ResendActivationEmail.as_view(), name='resend_email'),

    path('me/', UserDetailAPIView.as_view(), name='user-detail'),

    path('preferences/',
         UserPreferenceAPIView.as_view(), name='user_preferences'),
    path('translation/<str:language>/',
         TranslationAPIView.as_view(), name='get_translation'),

    path('phone_numbers/', UserPhoneNumberAPIView.as_view(),
         name='user-phone-numbers'),
    path('phone_numbers/<int:pk>/', UserPhoneNumberAPIView.as_view(),
         name='user-phone-number-detail'),


    # url(r'^password-reset/validate_token/',
    # reset_password_validate_token, name="reset-password-validate"),
    # url(r'^password-reset/confirm/',
    # reset_password_confirm, name="reset-password-confirm"),
    # url(r'^password-reset/',
    # MetutorsResetPasswordRequestToken.as_view(), name="reset-password-request"),

    # path('request_forget_username_sms/', RequestForgetUsername.as_view()),
    # path(r'^forgot_username/', ForgetUsername.as_view(), name="forget_password"),


]
