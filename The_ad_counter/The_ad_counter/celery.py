import os
from django.conf import settings

from celery import Celery

# Установка переменной окружения для настроек Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'The_ad_counter.settings')

app = Celery('The_ad_counter', broker=settings.CELERY_BROKER_URL)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автообнаружение задач в приложениях Django
app.autodiscover_tasks()

# Планировщик задач
app.conf.beat_schedule = {
    'check-adds-every-hour': {
        'task': 'counterapp.tasks.adding_tasks_to_delay',
        'schedule': settings.CELERY_SCHEDULE,
    },
}