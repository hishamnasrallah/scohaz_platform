from django.urls import path

from version.apis.views import CheckVersion, LatestVersionAPIView

urlpatterns = [
    path('check-version/', CheckVersion.as_view()),
    path('latest-version/<str:lang>/',
         LatestVersionAPIView.as_view(), name='latest-version'),

]
