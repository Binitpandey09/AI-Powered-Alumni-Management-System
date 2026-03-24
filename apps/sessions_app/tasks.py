from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_session_reminder(self, session_id):
    """Send reminder email to all confirmed students 1 hour before session."""
    try:
        from .models import Session, Booking
        from django.core.mail import send_mail
        from django.conf import settings

        session = Session.objects.select_related('host').get(pk=session_id)
        confirmed_bookings = Booking.objects.filter(
            session=session, status='confirmed'
        ).select_related('student')

        for booking in confirmed_bookings:
            student = booking.student
            meeting_info = f'\nMeeting Link: {session.meeting_link}' if session.meeting_link else ''
            send_mail(
                subject=f'Reminder: {session.title} starts in 1 hour',
                message=(
                    f'Hi {student.first_name},\n\n'
                    f'Your session "{session.title}" with {session.host.full_name} '
                    f'starts in 1 hour at {session.scheduled_at.strftime("%I:%M %p")}.'
                    f'{meeting_info}\n\n'
                    f'Duration: {session.duration_minutes} minutes\n\n'
                    f'— AlumniAI Team'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[student.email],
                fail_silently=True,
            )

        logger.info(f'Sent reminders for session {session_id} to {confirmed_bookings.count()} students.')
    except Exception as exc:
        logger.error(f'send_session_reminder failed for session {session_id}: {exc}')
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def mark_session_completed(self, session_id):
    """Mark session and all confirmed bookings as completed, email students for review."""
    try:
        from .models import Session, Booking
        from django.core.mail import send_mail
        from django.conf import settings

        session = Session.objects.get(pk=session_id)

        if session.status in ('cancelled',):
            logger.info(f'Session {session_id} is cancelled — skipping completion.')
            return

        session.status = 'completed'
        session.save(update_fields=['status'])

        confirmed_bookings = Booking.objects.filter(
            session=session, status='confirmed'
        ).select_related('student')

        for booking in confirmed_bookings:
            booking.status = 'completed'
            booking.save(update_fields=['status'])

            student = booking.student
            review_url = f'/api/sessions/bookings/{booking.id}/review/'
            send_mail(
                subject=f'How was your session: {session.title}?',
                message=(
                    f'Hi {student.first_name},\n\n'
                    f'Your session "{session.title}" has ended. '
                    f'We\'d love to hear your feedback!\n\n'
                    f'Leave a review at: {review_url}\n\n'
                    f'— AlumniAI Team'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[student.email],
                fail_silently=True,
            )

        logger.info(f'Session {session_id} marked completed. {confirmed_bookings.count()} bookings updated.')
    except Exception as exc:
        logger.error(f'mark_session_completed failed for session {session_id}: {exc}')
        raise self.retry(exc=exc, countdown=60)


@shared_task
def schedule_session_tasks(session_id):
    """Schedule reminder and completion tasks for a session."""
    try:
        from .models import Session
        import datetime

        session = Session.objects.get(pk=session_id)

        # Reminder: 1 hour before session
        reminder_eta = session.scheduled_at - datetime.timedelta(hours=1)
        if reminder_eta > timezone.now():
            send_session_reminder.apply_async(
                args=[session_id],
                eta=reminder_eta,
            )

        # Completion: session end + 30 min grace period
        completion_eta = session.scheduled_at + datetime.timedelta(
            minutes=session.duration_minutes + 30
        )
        if completion_eta > timezone.now():
            mark_session_completed.apply_async(
                args=[session_id],
                eta=completion_eta,
            )

        logger.info(
            f'Scheduled tasks for session {session_id}: '
            f'reminder at {reminder_eta}, completion at {completion_eta}'
        )
    except Exception as exc:
        logger.error(f'schedule_session_tasks failed for session {session_id}: {exc}')
