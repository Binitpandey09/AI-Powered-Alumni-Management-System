from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_notification_email(self, user_id, title, message):
    """Send an email notification to a user."""
    try:
        from django.contrib.auth import get_user_model
        from django.core.mail import send_mail
        from django.conf import settings

        User = get_user_model()
        user = User.objects.get(pk=user_id)

        send_mail(
            subject=title,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return f'Email sent to {user.email}'
    except Exception as exc:
        logger.warning('send_notification_email failed for user %s: %s', user_id, exc)
        raise self.retry(exc=exc)


@shared_task
def cleanup_old_notifications():
    """Delete read notifications older than 90 days."""
    from apps.notifications.models import Notification

    cutoff = timezone.now() - timedelta(days=90)
    deleted_count, _ = Notification.objects.filter(
        is_read=True,
        created_at__lt=cutoff,
    ).delete()

    logger.info('cleanup_old_notifications: deleted %d notifications', deleted_count)
    return deleted_count


@shared_task
def send_session_reminders():
    """
    Send reminders for sessions starting in the next 24 hours.
    Runs every 30 minutes via Celery Beat.
    """
    from apps.sessions_app.models import Booking
    from utils.notify import send_notification

    now = timezone.now()
    window_start = now + timedelta(hours=1)
    window_end = now + timedelta(hours=25)

    bookings = (
        Booking.objects
        .filter(
            status='confirmed',
            session__scheduled_at__gte=window_start,
            session__scheduled_at__lte=window_end,
            reminder_sent=False,
        )
        .select_related('student', 'session', 'session__host')
    )

    sent = 0
    for booking in bookings:
        session = booking.session
        hours_away = int((session.scheduled_at - now).total_seconds() // 3600)

        send_notification(
            user=booking.student,
            notif_type='session',
            title='Session Reminder',
            message=f'Your session "{session.title}" starts in ~{hours_away} hour(s).',
            link=f'/sessions/{session.id}/',
        )
        send_notification(
            user=session.host,
            notif_type='session',
            title='Upcoming Session',
            message=f'Your session "{session.title}" starts in ~{hours_away} hour(s).',
            link=f'/sessions/{session.id}/',
        )

        # Mark reminder sent to avoid duplicates
        Booking.objects.filter(pk=booking.pk).update(reminder_sent=True)
        sent += 1

    logger.info('send_session_reminders: sent %d reminders', sent)
    return f'Sent {sent} session reminders'
