"""
Celery application for FinAI.

Start worker:
    celery -A FinAI worker -l info

Start beat scheduler (periodic tasks):
    celery -A FinAI beat -l info
"""
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FinAI.settings')

app = Celery('FinAI')

# Use Django settings prefixed with CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all INSTALLED_APPS
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
