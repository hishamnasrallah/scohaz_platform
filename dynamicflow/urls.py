from django.urls import path
from dynamicflow.apis.views import FlowAPIView

urlpatterns = [

    path('service_flow/', FlowAPIView.as_view(),
         name='services_flow'),

]
