"""
Django settings for geodjango project.

Generated by 'django-admin startproject' using Django 3.1.4.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

from pathlib import Path
from os import getenv
import sys

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

sys.path.insert(0, BASE_DIR.parent.as_posix())
import secret_settings as secrets

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = secrets.NATURWB_DJANGO_SECRET_KEY
# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG = True
DEBUG = secrets.NATURWB_DJANGO_DEBUG
if DEBUG is None:
    DEBUG = False

ALLOWED_HOSTS = [
    "naturwb.dev.wwl-web.de",
    "localhost",
    "127.0.0.1",
    "naturwb.de",
    "www.naturwb.de"
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'leaflet',
    # 'sitetree',
    'request', # for statistics
    'django_q', # for task queue
    'google_site_verification', 
    # own
    'naturwb',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'request.middleware.RequestMiddleware',
]

ROOT_URLCONF = 'geodjango.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR.joinpath("templates")],
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

WSGI_APPLICATION = 'geodjango.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    'default':{
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': secrets.NATURWB_DB_NAME,
        'USER': secrets.NATURWB_DB_USER,
        'PASSWORD': secrets.NATURWB_DB_PWD,
        'HOST': secrets.NATURWB_DB_HOST,
        'PORT': secrets.NATURWB_DB_PORT,
        }
}
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = 'de-de'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / "naturwb/static",
]

STATIC_ROOT = BASE_DIR / "static_root" # static directory on the server side to deploy data to, use manage.py collectstatic to fill

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# leaflet configuration
LEAFLET_CONFIG = {
    #'SRID':"EPSG:31467",
    'TILES_EXTENT': [7.5000, 47.2700, 10.5000, 55.0600],#[924861,6375196,985649,6448688],
    'DEFAULT_CENTER': (51.351, 10.459),
    'DEFAULT_ZOOM': 6,
    'NO_GLOBALS': False, # neu
    'PLUGINS': { # neu
        'forms': {
            'auto-include': True
        }
    }
}


# CSFR Security
if DEBUG:
    SECURE_SSL_REDIRECT = False
else:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True

# upload limitation
DATA_UPLOAD_MAX_MEMORY_SIZE = 8 * 1024 * 1024

# User authentification
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# for user statistics request
REQUEST_LOG_IP=False
REQUEST_LOG_USER=False

# Configure your Q cluster
# More details https://django-q.readthedocs.io/en/latest/configure.html
Q_CLUSTER = {
    "name": "naturwb",
    "orm": "default",  # Use Django's ORM + database for broker
    "timeout": 5,
    "max_attempts": 4,
    "retry": 30
}

GOOGLE_SITE_VERIFICATION_FILE = secrets.NATURWB_GOOGLE_VERIFICATION

GDAL_LIBRARY_PATH = getenv("GDAL_LIBRARY_PATH")
GEOS_LIBRARY_PATH = getenv("GEOS_LIBRARY_PATH")

del secrets

# Logging configuration
from aldjemy.core import get_engine
with get_engine().connect() as conn:
    do_logging = conn.execute(
        "SELECT value FROM naturwb_settings WHERE name='write_logs';").first()[0]
if do_logging:
    log_file = BASE_DIR.joinpath('logs/naturwb.de_debug.log')
    if log_file.is_file(): log_file.unlink()
    with open(log_file, 'w') as f:
        f.write("")
    log_file.chmod(0o777)
    LOGGING = { 
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'file': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'filename': log_file,
            },
        },
        'loggers': {
            'django': {
                'handlers': ['file'],
                'level': 'DEBUG',
                'propagate': True,
            },
        },
    }
