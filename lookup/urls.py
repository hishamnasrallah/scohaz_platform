from django.urls import path, include
from rest_framework.routers import DefaultRouter

from lookup.apis.views import RetrieveLookupsListAPIView, LookupViewSet

router = DefaultRouter()
router.register(r'', LookupViewSet, basename='lookup')

urlpatterns = [
    path('management/', include(router.urls)),
]
urlpatterns += [
    path('', RetrieveLookupsListAPIView.as_view(), name='lookups'),
]

