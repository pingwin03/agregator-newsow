import os
from celery import Celery

# ZMIANA: tutaj musi być 'core.settings', a nie 'agregator_newsow.settings'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# ZMIANA: tutaj również zmieniamy nazwę aplikacji na 'core'
app = Celery('core')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()