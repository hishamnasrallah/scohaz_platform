import os

from .common import (BASE_DIR, INSTALLED_APPS, MIDDLEWARE, DATABASES,
                     STATIC_URL, SECRET_KEY, ROOT_URLCONF, TEMPLATES,
                     WSGI_APPLICATION, DEBUG, ALLOWED_HOSTS,
                     AUTH_PASSWORD_VALIDATORS, LANGUAGE_CODE, TIME_ZONE,
                     USE_I18N, USE_TZ, DEFAULT_AUTO_FIELD,
                     MEDIA_ROOT, MEDIA_URL, STATIC_ROOT, CSRF_TRUSTED_ORIGINS)

from icecream import ic
from datetime import timedelta
from os import environ as ENV
from dotenv import load_dotenv
# Load the environment variables from the .env file
load_dotenv()

# gettext = lambda s: s

DEBUG = DEBUG
BASE_DIR = BASE_DIR
INSTALLED_APPS = INSTALLED_APPS
_MIDDLEWARE = MIDDLEWARE
DATABASES = DATABASES
STATIC_URL = STATIC_URL
SECRET_KEY = SECRET_KEY
ROOT_URLCONF = ROOT_URLCONF
TEMPLATES = TEMPLATES
WSGI_APPLICATION = WSGI_APPLICATION
ALLOWED_HOSTS = ALLOWED_HOSTS
AUTH_PASSWORD_VALIDATORS = AUTH_PASSWORD_VALIDATORS
LANGUAGE_CODE = LANGUAGE_CODE
TIME_ZONE = TIME_ZONE
USE_I18N = USE_I18N
USE_TZ = USE_TZ
DEFAULT_AUTO_FIELD = DEFAULT_AUTO_FIELD
MEDIA_ROOT = MEDIA_ROOT
MEDIA_URL = MEDIA_URL
STATIC_ROOT = STATIC_ROOT
CSRF_TRUSTED_ORIGINS = CSRF_TRUSTED_ORIGINS
INSTALLED_APPS += [
    # "debug_toolbar",
    # "silk",
    "django_prometheus",
    "corsheaders",
    # "django_extensions",
    'rest_framework',
    "celery",
    "django_celery_beat",
    "django_celery_results"

]

CUSTOM_APPS = [
    'bbb_app',
    'aaa_app',
    'relational_app',
    'samer_app',
    'assets_app',
    'asset_app',
    'contact2_app',
    'omar',
    'testchoice',
    'hr',
    'crm',

]
INSTALLED_APPS += CUSTOM_APPS + [

    "authentication",
    "lookup",
    "conditional_approval",
    "case",
    "dynamicflow",
    "misc",
    "version",
    "integration",
    "license_subscription_manager",
    "app_builder",
    "version_control"
    # "lowcode",
]

# APPS_CURRENT_USER_MIDDLEWARE = {
#     'contact_app': [
#         'contact_app.middleware.CurrentUserMiddleware',
#     ],
#     'omar': [
#         'omar.middleware.CurrentUserMiddleware',
#     ],
#     'testchoice': [
#         'testchoice.middleware.CurrentUserMiddleware',
#     ],
#     'hr': [
#         'hr.middleware.CurrentUserMiddleware',
#     ],
#     'crm': [
#         'crm.middleware.CurrentUserMiddleware',
#     ],
# }
APPS_CURRENT_USER_MIDDLEWARE = [
    'bbb_app.middleware.CurrentUserMiddleware',
    'aaa_app.middleware.CurrentUserMiddleware',
    'relational_app.middleware.CurrentUserMiddleware',
    'samer_app.middleware.CurrentUserMiddleware',
    'assets_app.middleware.CurrentUserMiddleware',
    'asset_app.middleware.CurrentUserMiddleware',
    'contact2_app.middleware.CurrentUserMiddleware',
    'omar.middleware.CurrentUserMiddleware',
    'testchoice.middleware.CurrentUserMiddleware',
    'hr.middleware.CurrentUserMiddleware',
    #// TODO: add other modules
    'crm.middleware.CurrentUserMiddleware',
]

APP_MIDDLEWARE_MAPPING = {
    'bbb_app': [
        'bbb_app.middleware.DynamicModelMiddleware',
    ],
    'aaa_app': [
        'aaa_app.middleware.DynamicModelMiddleware',
    ],
    'relational_app': [
        'relational_app.middleware.DynamicModelMiddleware',
    ],
    'samer_app': [
        'samer_app.middleware.DynamicModelMiddleware',
    ],
    'assets_app': [
        'assets_app.middleware.DynamicModelMiddleware',
    ],
    'asset_app': [
        'asset_app.middleware.DynamicModelMiddleware',
    ],
    'contact2_app': [
        'contact2_app.middleware.DynamicModelMiddleware',
    ],

    'omar': [
        'omar.middleware.DynamicModelMiddleware',
    ],


    'testchoice': [
        'testchoice.middleware.DynamicModelMiddleware',
    ],
    'hr': [
        'hr.middleware.DynamicModelMiddleware',
    ],

    'crm': [
        'crm.middleware.DynamicModelMiddleware',
    ],


}

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "scohaz_platform.middleware.MiddlewareRouter",
    *_MIDDLEWARE,
    # "license_subscription_manager.middleware.SubscriptionLicenseMiddleware",
    # "debug_toolbar.middleware.DebugToolbarMiddleware",
    # "silk.middleware.SilkyMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]


INTERNAL_IPS = ["127.0.0.1"]

# Allow specific domains for CORS
CORS_ALLOWED_ORIGINS = [
    "https://your-frontend-domain.com",
    "https://another-trusted-domain.com",
    "http://localhost:5173",
]

# Alternatively, for dev only (NOT for production):
CORS_ALLOW_ALL_ORIGINS = True

AUTH_USER_MODEL = 'authentication.CustomUser'

SITE_ID = int(os.environ.get("SITE_ID", None)) if os.environ.get("SITE_ID") else None


REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated'
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',

        'rest_framework.authentication.BasicAuthentication',
        # // TODO: you can remove the following line if
        # // you dont need sessions -- specially on production --
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema'
}


SIMPLE_JWT = {
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer', 'JWT',),
    'USER_ID_FIELD': 'id',
    'AUTH_TOKEN_CLASSES': ('authentication.tokens.ScohazToken',),
    'USER_ID_CLAIM': 'uid',
    'TOKEN_TYPE_CLAIM': 'typ',
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=100000),
    'REFRESH_TOKEN_LIFETIME': timedelta(weeks=2),
}


SENDGRID_API_KEY = ENV.get(
    'SENDGRID_API_KEY',
    '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')
EMAIL_HOST = ENV.get('EMAIL_HOST', 'smtp.sendgrid.net')
EMAIL_HOST_USER = ENV.get('EMAIL_HOST_USER', 'apikey')
EMAIL_HOST_PASSWORD = ENV.get('EMAIL_HOST_PASSWORD', SENDGRID_API_KEY)
EMAIL_PORT = ENV.get('EMAIL_PORT', 587)
EMAIL_USE_TLS = True
EMAIL_SENDER = ENV.get('EMAIL_SENDER',
                       'Vscribe Team <no-reply@kaptions.com>')
EMAIL_VERIFICATION_TEMPLATE_ID = ENV.get(
    'EMAIL_VERIFICATION_TEMPLATE_ID',
    '8a146eb2-4c8c-418f-9a49-bb062309628d')

DOMAIN = ENV.get('DOMAIN', 'http://127.0.0.1:8002')
FE_DOMAIN = ENV.get('FE_DOMAIN', 'https://vscribev2.tarjama.com/')

CELERY_RESULT_BACKEND = "django-db"
CELERY_BROKER_URL = 'redis://localhost:6379/0'
## CELERY_RESULT_BACKEND = 'redis://localhost:6379'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers.DatabaseScheduler'
CELERY_TIMEZONE = 'UTC'

if not DEBUG:  # Disable ic in production
    ic.disable()


# settings.py

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'django_logs.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'myapp': {  # You can create custom loggers for your app
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
