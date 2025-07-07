"""
URL configuration for scohaz_platform project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework.documentation import include_docs_urls
from django.conf.urls.static import static
from rest_framework.decorators import api_view, permission_classes
from django.views.static import serve
from rest_framework.permissions import IsAuthenticated
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework.permissions import AllowAny

from scohaz_platform.apis.views import ApplicationURLsView, CategorizedApplicationURLsView
from scohaz_platform.settings import settings, CUSTOM_APPS

# API Documentation Schema
schema_view = get_schema_view(
    openapi.Info(
        title="Dynamic API Documentation",
        default_version='v1',
        description="API documentation for dynamically generated apps",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="support@example.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include("authentication.urls")),
    path('authentication/', include("authentication.urls")),
    # path('reports/', include("reporting.urls")),
    path('reports/', include("reporting_templates.urls")),
    path('app_builder/', include("app_builder.urls")),
    path('lookups/', include("lookup.urls")),
    path('case/', include("case.urls")),
    path("", include("django_prometheus.urls")),
    path('api-docs/', include_docs_urls(title='API Documentation')),
    path('dynamic/', include('dynamicflow.urls'), name='dynamicflow'),
    path('version/', include('version.urls'), name='version'),
    path('integration/', include('integration.urls'), name='integartion'),
    path('translations/', include('misc.urls')),  # Include translations app URLs
    path('define/', include("lowcode.urls"), name='Project Design'),
    path('conditional_approvals/', include("conditional_approval.urls"), name='Conditional Approvals'),
    path('license/', include("license_subscription_manager.urls"), name='license_subscription_manager'),
    path('app-builder/', include('app_builder.urls')),
    # path('my_dynamic_app/', include('my_dynamic_app.urls')),
    path('api-docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api-redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    # Include dynamically registered app URLs
    path('api/applications/urls/', ApplicationURLsView.as_view(), name='application_urls'),
    path('api/applications/categorized-urls/', CategorizedApplicationURLsView.as_view(), name='categorized_application_urls'),
]

# Dynamically register app URLs
for app_name in CUSTOM_APPS:  # Assume CUSTOM_APPS holds dynamically registered apps
    urlpatterns.append(path(f'{app_name}/', include(f'{app_name}.urls')))

@api_view(['GET'])
@permission_classes((IsAuthenticated, ))
def protected_serve(request, path, document_root=None, show_indexes=False):
    return serve(request, path, document_root, show_indexes)


if settings.DEBUG:
    urlpatterns += [
        re_path(r'^%s(?P<path>.*)$' % settings.MEDIA_URL[1:],
                protected_serve,
                {'document_root': settings.MEDIA_ROOT}),
    ]

else:
    urlpatterns += [
        re_path(r'^%s(?P<path>.*)$' % settings.MEDIA_URL[1:],
                protected_serve,
                {'document_root': settings.MEDIA_ROOT}
                )]

if not settings.DEBUG:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
        re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    ]

# if settings.DEBUG:  # Only enable in DEBUG mode
#     urlpatterns += [
#         path("silk/", include("silk.urls")),
#         path("__debug__/", include("debug_toolbar.urls")),
#
#     ]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
