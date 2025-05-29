from django.urls import path
from . import views

urlpatterns = [
    path('repositories/', views.repository_list, name='repository_list'),
    path('repositories/<int:pk>/', views.repository_detail, name='repository_detail'),
]
