from django.urls import path

from lookup.apis.views import RetrieveLookupsListAPIView

urlpatterns = [
    path('', RetrieveLookupsListAPIView.as_view(), name='lookups'),
]
