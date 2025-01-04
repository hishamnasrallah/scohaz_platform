from django.urls import path
from .views.application_views import ApplicationListView, ApplicationDetailView

urlpatterns = [
    path('applications/', ApplicationListView.as_view(), name='application-list'),
    path('applications/<int:pk>/', ApplicationDetailView.as_view(), name='application-detail'),
]
