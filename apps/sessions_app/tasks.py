from celery import shared_task
from django.utils import timezone
from datetime import timedelta

@shared_task
def send_session_reminders():
    """Send reminders for upcoming sessions"""
    from .models import Session
    
    # Get sessions starting in the next hour
    upcoming_time = timezone.now() + timedelta(hours=1)
    sessions = Session.objects.filter(
        scheduled_time__lte=upcoming_time,
        scheduled_time__gte=timezone.now(),
        status='confirmed'
    )
    
    for session in sessions:
        # Send reminder email/notification
        pass
    
    return f"Sent reminders for {sessions.count()} sessions"
