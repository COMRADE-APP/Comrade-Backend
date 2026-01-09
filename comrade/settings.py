"""
Django settings for comrade project.
"""

from pathlib import Path
from datetime import timedelta
import os
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-c+%9#v0&z&-av-84em1*d3aazv4$-v&z=8b1&93r%iw*0js+m=')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True') == 'True'

# ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost:3000,127.0.0.1:8000').split(',')
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "[::1]",
    "http://localhost:8000",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Custom Apps
    'Authentication',
    'rest_framework',
    'UserManagement',
    'Rooms',
    'Announcements',
    'Events',
    'Resources',
    'Specialization',
    'Organisation',
    'Institution',
    'Task',
    'Payment',
    'Research',
    'Verification',  # New verification system
    
    # Authentication Support Apps
    'DeviceManagement',
    'ActivityLog',
    
    # JWT and Social Auth
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.twitter_oauth2',
    'allauth.socialaccount.providers.github',
    'allauth.socialaccount.providers.apple',
    'allauth.socialaccount.providers.linkedin_oauth2',
    'allauth.socialaccount.providers.microsoft',

]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "allauth.account.middleware.AccountMiddleware",
]

# ALLOWED_HOSTS: Only hostnames, no protocols/ports
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "[::1]",
]

# CORS settings - FIX THESE
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# CRITICAL: This must be True for cookies/session auth
# CORS_ALLOW_CREDENTIALS = True


# CSRF settings - CRITICAL for POST requests
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Additional CORS headers needed
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'access-control-allow-credentials',  # Add this
]

# Add these settings for better CORS handling
CORS_EXPOSE_HEADERS = ['Content-Type', 'X-CSRFToken']
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https?://localhost:8000$",
    r"^https?://localhost:8080$",
    r"^https?://localhost:5173$",
]

# CSRF_COOKIE_SECURE = False
# SESSION_COOKIE_SECURE = False

# CORS_ALLOW_CREDENTIALS = True



# If you want to disable CSRF for testing (not recommended for production)
# CSRF_COOKIE_SECURE = False  # Set to True in production with HTTPS
# SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS

# ALLOWED_HOSTS = [
#     "localhost",
#     "127.0.0.1",
#     "[::1]",
#     "localhost:8000",
#     "localhost:3000",
#     "localhost:5173",
#     "localhost:8080",
# ]

# Twilio configuration
ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
COUNTRY_CODE = os.getenv('COUNTRY_CODE', '')
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER', '')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')

# Email configuration
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', ''))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)

ROOT_URLCONF = 'comrade.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'comrade.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': os.getenv('RATE_LIMIT_ANON', '100/hour'),
        'user': os.getenv('RATE_LIMIT_USER', '1000/hour'),
        'login': os.getenv('RATE_LIMIT_LOGIN', '5/minute'),
        'otp': os.getenv('RATE_LIMIT_OTP', '3/hour'),
    },
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

AUTH_USER_MODEL = 'Authentication.CustomUser'
STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': os.getenv('GOOGLE_CLIENT_ID', ''),
            'secret': os.getenv('GOOGLE_CLIENT_SECRET', ''),
            'key': ''
        },
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online', 'prompt': 'consent'},
    },
    'facebook': {
        'APP': {
            'client_id': os.getenv('FACEBOOK_CLIENT_ID', ''),
            'secret': os.getenv('FACEBOOK_CLIENT_SECRET', ''),
            'key': ''
        },
        'SCOPE': ['email', 'public_profile'],
        'AUTH_PARAMS': {'auth_type': 'reauthenticate'},
    },
    'twitter': {
        'APP': {
            'client_id': os.getenv('TWITTER_CLIENT_ID', ''),
            'secret': os.getenv('TWITTER_CLIENT_SECRET', ''),
            'key': ''
        },
        'SCOPE': ['email', 'public_profile'],
        'AUTH_PARAMS': {'auth_type': 'reauthenticate'},
    },
    'linkedin': {
        'APP': {
            'client_id': os.getenv('LINKEDIN_CLIENT_ID', ''),
            'secret': os.getenv('LINKEDIN_CLIENT_SECRET', ''),
            'key': ''
        },
        'SCOPE': ['email', 'public_profile'],
        'AUTH_PARAMS': {'auth_type': 'reauthenticate'},
    },
    'github': {
        'APP': {
            'client_id': os.getenv('GITHUB_CLIENT_ID', ''),
            'secret': os.getenv('GITHUB_CLIENT_SECRET', ''),
            'key': ''
        },
        'SCOPE': ['email', 'public_profile'],
        'AUTH_PARAMS': {'auth_type': 'reauthenticate'},
    },
    'apple': {
        'APP': {
            'client_id': os.getenv('APPLE_CLIENT_ID', ''),
            'secret': os.getenv('APPLE_CLIENT_SECRET', ''),
            'key': ''
        },
        'SCOPE': ['email', 'public_profile'],
        'AUTH_PARAMS': {'auth_type': 'reauthenticate'},
    },
    'microsoft': {
        'APP': {
            'client_id': os.getenv('MICROSOFT_CLIENT_ID', ''),
            'secret': os.getenv('MICROSOFT_CLIENT_SECRET', ''),
            'key': ''
        },
        'SCOPE': ['email', 'public_profile'],
        'AUTH_PARAMS': {'auth_type': 'reauthenticate'},
    },
}

# Account adapter for custom user model
ACCOUNT_ADAPTER = 'Authentication.adapters.MyAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'Authentication.adapters.MySocialAccountAdapter'

# Email-only authentication (NO USERNAME) - Updated for allauth v0.50+
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_LOGIN_METHODS = {'email'}  # New v0.50+ syntax
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']  # New v0.50+ syntax
ACCOUNT_EMAIL_VERIFICATION = 'optional'  # Can be 'mandatory' for production
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_SUBJECT_PREFIX = '[Comrade] '

# Social account settings
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'  # Trust OAuth providers
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_STORE_TOKENS = True

# Redirect URLs - Point to frontend
# NOTE: Frontend runs on port 5173 (Vite) by default, ensure FRONTEND_URL has trailing slash
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173/')

# Dashboard is at root '/' in frontend
FRONTEND_DASHBOARD = FRONTEND_URL  # Frontend dashboard is at '/'
LOGIN_REDIRECT_URL = FRONTEND_DASHBOARD
ACCOUNT_LOGIN_REDIRECT_URL = FRONTEND_DASHBOARD
ACCOUNT_SIGNUP_REDIRECT_URL = FRONTEND_DASHBOARD
SOCIALACCOUNT_LOGIN_REDIRECT_URL = FRONTEND_DASHBOARD
LOGOUT_REDIRECT_URL = f"{FRONTEND_URL}login"



# Django AllAuth settings for development
SITE_ID = 1

# Allow HTTP for development (change to 'https' in production)
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http"

# These settings help with cross-origin requests
ACCOUNT_EMAIL_VERIFICATION = 'optional'  # Set to 'mandatory' in production
ACCOUNT_SESSION_REMEMBER = True

# Cookie settings for development
# CSRF_COOKIE_SAMESITE = 'Lax'
# SESSION_COOKIE_SAMESITE = 'Lax'
# CSRF_COOKIE_HTTPONLY = False  # Allows JS to read CSRF token
# SESSION_COOKIE_HTTPONLY = True
# CSRF_COOKIE_SECURE = False  # Set to True in production with HTTPS
# SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
# CSRF_COOKIE_DOMAIN = None  # Use None for localhost
# SESSION_COOKIE_DOMAIN = None  # Use None for localhost


