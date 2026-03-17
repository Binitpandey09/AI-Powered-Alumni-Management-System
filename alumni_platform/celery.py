import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alumni_platform.settings')

app = Celery('alumni_platform')

# Load config from Django settings with CELERY namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()

# Celery Beat Schedule for periodic tasks
app.conf.beat_schedule = {
    'send-session-reminders': {
        'task': 'apps.sessions_app.tasks.send_session_reminders',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    'process-pending-payments': {
        'task': 'apps.payments.tasks.process_pending_payments',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    'cleanup-expired-notifications': {
        'task': 'apps.notifications.tasks.cleanup_old_notifications',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
