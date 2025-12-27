from pathlib import Path
from .env_config import get_env_variable

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# =============================================================================
# БАЗОВЫЕ НАСТРОЙКИ ПРОЕКТА
# =============================================================================

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_env_variable('SECRET_KEY', 'django-insecure-^_srr*25_&y_pjgm*s7z8hd*enoin7^13%h_^sskee(h22)usx')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = get_env_variable('DEBUG', True, bool)

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']  # Для тестирования


# =============================================================================
# ОПРЕДЕЛЕНИЕ ПРИЛОЖЕНИЙ
# =============================================================================

INSTALLED_APPS = [
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party packages
    "drf_spectacular",
    "django_filters",
    "rest_framework",
    'rest_framework.authtoken',
    'corsheaders',  # Добавлено для поддержки CORS

    # REST authentication
    'dj_rest_auth',

    # Local apps
    "apps.services.authentication",
    "apps.services.notifications",
    "apps.core",
    "apps.registry.partners",
]


# =============================================================================
# ПРОЧИЕ НАСТРОЙКИ DJANGO
# =============================================================================

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Добавлено для поддержки CORS
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    'django.middleware.locale.LocaleMiddleware',
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# =============================================================================
# НАСТРОЙКИ БАЗЫ ДАННЫХ
# =============================================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# =============================================================================
# ВАЛИДАЦИЯ ПАРОЛЕЙ
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# =============================================================================
# ЛОКАЛИЗАЦИЯ И ВРЕМЯ
# =============================================================================

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_L10N = True
USE_TZ = True

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]


# =============================================================================
# СТАТИЧЕСКИЕ ФАЙЛЫ И МЕДИА
# =============================================================================

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / 'staticfiles'  # Для collectstatic


# =============================================================================
# ПОЛЯ ПО УМОЛЧАНИЮ
# =============================================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# =============================================================================
# НАСТРОЙКИ АУТЕНТИФИКАЦИИ
# =============================================================================

# Бэкенды аутентификации
AUTHENTICATION_BACKENDS = [
    # Используем стандартные методы аутентификации Django
    'django.contrib.auth.backends.ModelBackend',
]

# URL перенаправления для стандартной аутентификации Django
LOGIN_REDIRECT_URL = '/'  # После успешного входа в админку
LOGOUT_REDIRECT_URL = '/'  # После выхода



# =============================================================================
# НАСТРОЙКИ DRF (DJANGO REST FRAMEWORK)
# =============================================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        'rest_framework.authentication.TokenAuthentication',
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',  # Для удобства разработки
    ],
}


# =============================================================================
# НАСТРОЙКИ DJ-REST-AUTH
# =============================================================================

REST_AUTH = {
    'USE_JWT': False,  # Используем Token аутентификацию
    'TOKEN_MODEL': 'rest_framework.authtoken.models.Token',
    'JWT_AUTH_COOKIE': None,
    'JWT_AUTH_REFRESH_COOKIE': None,
    'SESSION_LOGIN': False,  # Отключаем сессионный логин, используем токены
    'OLD_PASSWORD_FIELD_ENABLED': True,
    'LOGOUT_ON_PASSWORD_CHANGE': False,

    # Сериализаторы
    'USER_DETAILS_SERIALIZER': 'dj_rest_auth.serializers.UserDetailsSerializer',
    'TOKEN_SERIALIZER': 'dj_rest_auth.serializers.TokenSerializer',
}


# =============================================================================
# НАСТРОЙКИ DRF-SPECTACULAR (ДОКУМЕНТАЦИЯ API)
# =============================================================================

SPECTACULAR_SETTINGS = {
    "TITLE": "Partner Registry API",
    "DESCRIPTION": "API для управления партнерами и их сотрудниками",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api/",
    
    # Автоматическая документация эндпоинтов
    "SCHEMA_COERCE_PATH_PK_SUFFIX": True,
    "SCHEMA_COERCE_METHOD_NAMES": {
        "create": "create",
        "list": "list",
        "retrieve": "retrieve",
        "update": "update",
        "partial_update": "partial_update",
        "destroy": "destroy",
    },
    
    # Безопасность
    "SECURITY": [
        {
            "TokenAuth": [],
        }
    ],
    "SECURITY_DEFINITIONS": {
        "TokenAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Token-based authentication with format: Token <your_token>"
        }
    },
}


# =============================================================================
# НАСТРОЙКИ ДЛЯ РАЗРАБОТКИ
# =============================================================================

if DEBUG:
    # Дополнительные настройки для отладки
    INTERNAL_IPS = ['127.0.0.1']
    
    # Расширенное логирование
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            'django': {
                'handlers': ['console'],
                'level': 'INFO',
            },
        },
    }

# =============================================================================
# НАСТРОЙКИ CORS (Для поддержки веб-запросов из Flutter-приложения)
# =============================================================================

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://localhost",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]

CORS_ALLOW_CREDENTIALS = True


# =============================================================================
# НАСТРОЙКИ ДЛЯ ЛОКАЛЬНОЙ РАЗРАБОТКИ - СИНХРОННАЯ ОБРАБОТКА ЗАДАЧ CELERY
# =============================================================================

# Для локальной разработки - синхронная обработка задач Celery
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Современные настройки Celery (для версии 4.0+)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_ALWAYS_EAGER = True