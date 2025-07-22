from django.urls import path

from mockapi.views.beneficiary_info import get_user_info


urlpatterns = [
    path('user_info/<str:national_number>/', get_user_info),
]
