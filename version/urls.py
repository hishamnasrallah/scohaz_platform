
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from version.apis.views import CheckVersion, LatestVersionAPIView, LanguageListView, \
    TranslationFileView, TranslationPartialUpdateView, AvailableLanguagesView, VersionViewSet

router = DefaultRouter()
router.register(r'versions', VersionViewSet, basename='version')

urlpatterns = [
    path('', include(router.urls)),
]
urlpatterns += [
    path('check-version/', CheckVersion.as_view()),
    path('latest-version/<str:lang>/',
         LatestVersionAPIView.as_view(), name='latest-version'),

    path('languages/available/', AvailableLanguagesView.as_view(), name='available-languages'),

    path('translation/languages/', LanguageListView.as_view(), name='language-list'),
    path('translation/<str:lang_code>/', TranslationFileView.as_view(), name='translation-read'),
    path('translation/<str:lang_code>/', TranslationFileView.as_view(), name='translation-put'),
    path('translations/<str:lang_code>/', TranslationPartialUpdateView.as_view(), name='translation-patch'),
    # path('translation/<str:lang_code>/', TranslationFileView.as_view(), name='translation-update'),

]
