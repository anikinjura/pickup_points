# config/celery.py
import os
from celery import Celery

# Установка переменной окружения для настроек Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Создание экземпляра Celery
app = Celery('pickup_points')

# Загрузка настроек из файла settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматическое обнаружение и регистрация задач
app.autodiscover_tasks()