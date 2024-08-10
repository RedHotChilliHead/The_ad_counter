"""
Django settings for The_ad_counter project.

Generated by 'django-admin startproject' using Django 5.0.7.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

from pathlib import Path
import sys
from celery.schedules import crontab

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure--^_22=#f^nd-qo16r%8bx!$&$bh=8pxk$*bm49=i-y^+7h&951'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["0.0.0.0", "127.0.0.1"]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'counterapp.apps.CounterappConfig',
    'rest_framework',
    'drf_spectacular',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'The_ad_counter.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
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

WSGI_APPLICATION = 'The_ad_counter.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'counter_db',
        'USER': 'postgres',
        'PASSWORD': 'admin',
        'HOST': 'db',
        'PORT': '5432',
    }
}

if 'test' in sys.argv or 'test_coverage' in sys.argv:
    DATABASES['default']['NAME'] = 'test_' + DATABASES['default']['NAME']

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Avito tech API",
    "DESCRIPTION": "The counter for the number of ads.",
    "VERSION": "0.0.1",
    'SERVE_INCLUDE_SCHEMA': False,
}

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

# Настройки Redis
RQ_QUEUES = {
    'default': {
        'HOST': 'localhost',
        'PORT': 6379,
        'DB': 0,
        'DEFAULT_TIMEOUT': None,  # Устанавливаем None, чтобы отключить таймаут для задач
        'DEFAULT_RESULT_TTL': None,  # Устанавливаем None, чтобы результат задачи не истекал
        'WORKER_CLASS': 'rq.worker.SimpleWorker',
    }
}

# CELERY_BROKER_URL = 'redis://localhost:6379/0'  # URL для подключения к Redis
# CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'  # URL для хранения результатов задач

CELERY_BROKER_URL = 'redis://redis:6379/0'  # URL для подключения к Redis
CELERY_RESULT_BACKEND = 'redis://redis:6379/0'  # URL для хранения результатов задач
# период обновления задач celery
if 'test' in sys.argv or 'test_coverage' in sys.argv:
    CELERY_SCHEDULE = 10.0  # для теста 10 секунд
else:
    # CELERY_SCHEDULE = 45.0  # для теста 45 секунд
    CELERY_SCHEDULE = crontab(minute=0, hour='*')  # для нормальной работы каждый час

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True  # Чтобы ошибки выбрасывались сразу

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
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
