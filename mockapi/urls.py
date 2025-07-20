from django.urls import path
from .views import get_user_info

urlpatterns = [
    path('user_info/<str:national_number>/', get_user_info),
]
