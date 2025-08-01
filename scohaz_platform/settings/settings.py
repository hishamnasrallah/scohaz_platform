import os

from .common import (BASE_DIR, INSTALLED_APPS, MIDDLEWARE, DATABASES,
                     STATIC_URL, SECRET_KEY, ROOT_URLCONF, TEMPLATES,
                     WSGI_APPLICATION, DEBUG, ALLOWED_HOSTS,
                     AUTH_PASSWORD_VALIDATORS, LANGUAGE_CODE, TIME_ZONE,
                     USE_I18N, USE_TZ, DEFAULT_AUTO_FIELD,
                     MEDIA_ROOT, MEDIA_URL, STATIC_ROOT, CSRF_TRUSTED_ORIGINS, TRANSLATION_DIR)

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
    "django_celery_results",
    "django_filters",
    'projects',
    'builder',
    'builds',


]

CUSTOM_APPS = [
    # 'ab_app',

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
    "version_control",
    "reporting",
    "reporting_templates",
    "simple_reporting",
    "mockapi",
    "inquiry"
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
    # 'ab_app.middleware.CurrentUserMiddleware',
    'reporting.middleware.CurrentUserMiddleware',
    #// TODO: add other modules
]

APP_MIDDLEWARE_MAPPING = {
    # 'ab_app': [
    #     'ab_app.middleware.DynamicModelMiddleware',
    # ],

    'reporting': [
        'reporting.middleware.DynamicModelMiddleware',
    ]

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


# Reporting Templates Configuration
REPORTING_TEMPLATES = {
    # Apps that can be used in reporting
    'ENABLED_APPS': INSTALLED_APPS,
    # ENABLED_APPS': [
    #     'authentication',
    #     'case',
    #     'lookup',
    #     'conditional_approval',
    #     # Add other apps you want to enable for reporting
    # ],

    # Default settings for new templates
    'DEFAULTS': {
        'PAGE_SIZE': 'A4',
        'ORIENTATION': 'portrait',
        'MARGINS': {
            'TOP': 72,    # 1 inch in points
            'BOTTOM': 72,
            'LEFT': 72,
            'RIGHT': 72,
        },
        'FONT_SIZE': 12,
        'FONT_FAMILY': 'Helvetica',
    },

    # Security settings
    'SECURITY': {
        # Maximum number of parameters allowed per template
        'MAX_PARAMETERS': 20,

        # Maximum execution time for data fetching (seconds)
        'DATA_FETCH_TIMEOUT': 30,

        # Maximum file size for generated PDFs (MB)
        'MAX_PDF_SIZE': 10,

        # Allow raw SQL queries
        'ALLOW_RAW_SQL': True,

        # Allow custom functions
        'ALLOW_CUSTOM_FUNCTIONS': True,
    },

    # Caching settings
    'CACHE': {
        # Cache backend to use for data sources
        'BACKEND': 'default',

        # Default cache timeout (seconds)
        'DEFAULT_TIMEOUT': 300,

        # Cache key prefix
        'KEY_PREFIX': 'pdf_report_',
    },

    # File storage settings
    'STORAGE': {
        # Storage backend for generated PDFs
        'BACKEND': 'django.core.files.storage.FileSystemStorage',

        # Path for storing generated PDFs
        'LOCATION': 'media/pdf_reports/',

        # Keep generated files for this many days
        'RETENTION_DAYS': 30,
    },

    # Font configuration
    'FONTS': {
        # Directory containing custom fonts
        'FONT_DIR': 'fonts/',

        # Arabic fonts configuration
        'ARABIC_FONTS': {
            'Arabic': 'NotoSansArabic-Regular.ttf',
            'Arabic-Bold': 'NotoSansArabic-Bold.ttf',
            'Arabic-Light': 'NotoSansArabic-Light.ttf',
        },

        # Additional fonts
        'CUSTOM_FONTS': {
            # 'FontName': 'filename.ttf',
        },
    },

    # Custom function modules
    'CUSTOM_FUNCTIONS': [
        'reporting_templates.custom_functions',
        # Add your custom function modules here
    ],

    # Parameter validation
    'PARAMETER_VALIDATION': {
        # Regex patterns for parameter types
        'PATTERNS': {
            'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'phone': r'^\+?1?\d{9,15}$',
            'url': r'^https?://[^\s]+$',
        },

        # Default validation rules
        'DEFAULTS': {
            'string': {'max_length': 255},
            'integer': {'min': -2147483648, 'max': 2147483647},
            'float': {'min': -999999999.99, 'max': 999999999.99},
        },
    },
}

EXCLUDED_PATHS = {
    "drf_format_suffix",
    "auth",
    "case",
    "api-docs",
    "version",
    "integration",
    "app-builder",
    "translations",
    "custom-action",
    "validation-rules",
    "integration-configs",
    "reports",
    "mock_api",
    "inquiry"
}

# Add reporting permissions to default groups (optional)
# DEFAULT_GROUP_PERMISSIONS = {
#     'managers': [
#         'reporting_templates.can_design_template',
#         'reporting_templates.can_generate_pdf',
#         'reporting_templates.can_generate_others_pdf',
#     ],
#     'emp1': [
#         'reporting_templates.can_generate_pdf',
#         'reporting_templates.can_generate_pdf',
#         'reporting_templates.can_generate_others_pdf',
#     ],
#     'Users': [
#         'reporting_templates.can_generate_pdf',
#     ],
# }

# Flutter SDK Path - it exists here!
FLUTTER_SDK_PATH = r'C:\flutter'

# Verify Flutter exists
flutter_exe = os.path.join(FLUTTER_SDK_PATH, 'bin', 'flutter.bat')
if os.path.exists(flutter_exe):
    print(f"✓ Flutter found at {flutter_exe}")
else:
    print(f"✗ Flutter NOT found at {flutter_exe}")

# Android SDK Path
ANDROID_SDK_PATH = r'C:\android-sdk'
ANDROID_CMDLINE_TOOLS = os.path.join(ANDROID_SDK_PATH, 'cmdline-tools', 'latest')

# Java path (update to your Java 17 path)
JAVA_HOME = r'C:\Program Files\Eclipse Adoptium\jdk-21.0.8.9-hotspot'

# Set environment variables
os.environ['FLUTTER_ROOT'] = FLUTTER_SDK_PATH
os.environ['ANDROID_HOME'] = ANDROID_SDK_PATH
os.environ['ANDROID_SDK_ROOT'] = ANDROID_SDK_PATH
os.environ['JAVA_HOME'] = JAVA_HOME

# Build complete PATH
flutter_bin = os.path.join(FLUTTER_SDK_PATH, 'bin')
android_bin = os.path.join(ANDROID_CMDLINE_TOOLS, 'bin')
java_bin = os.path.join(JAVA_HOME, 'bin')

# Add to PATH (put Flutter first)
os.environ['PATH'] = f"{flutter_bin};{android_bin};{java_bin};{os.environ.get('PATH', '')}"

# Build settings
BUILD_TIMEOUT = 600
USE_MOCK_BUILD = False

# Debug: Print PATH
print(f"PATH configured: {flutter_bin} is in PATH")