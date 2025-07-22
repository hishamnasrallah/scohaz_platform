from django.urls import path

from mockapi.views.beneficiary_info import get_user_info
from mockapi.views.payment import process_payment, check_payment_status

urlpatterns = [
    path('user_info/<str:national_number>/', get_user_info),
    path('payment/process/', process_payment, name='process_payment'),
    path('payment/status/<str:transaction_id>/', check_payment_status, name='check_payment_status'),
]
