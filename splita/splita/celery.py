import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'splita.settings')

app = Celery('splita')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule for periodic tasks
app.conf.beat_schedule = {
    'send-emi-reminders': {
        'task': 'notifications.tasks.send_emi_reminders',
        'schedule': 60.0 * 60 * 24,  # Run daily
    },
    'send-overdue-alerts': {
        'task': 'notifications.tasks.send_overdue_alerts',
        'schedule': 60.0 * 60 * 12,  # Run twice daily
    },
    'check-credit-utilization': {
        'task': 'notifications.tasks.check_credit_utilization',
        'schedule': 60.0 * 60 * 24,  # Run daily
    },
    'cleanup-old-notifications': {
        'task': 'notifications.tasks.cleanup_old_notifications',
        'schedule': 60.0 * 60 * 24 * 7,  # Run weekly
    },
}

app.conf.timezone = 'UTC'

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}') 