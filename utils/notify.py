"""
Central notification utility.

Usage:
    from utils.notify import send_notification

    send_notification(
        user=request.user,
        notif_type='booking_confirmed',
        title='Booking Confirmed',
        message='Your session is confirmed.',
        link='/sessions/',
    )

Always fails silently — never raises exceptions to callers.
"""
import logging

logger = logging.getLogger(__name__)

# Map notif_type prefix → NotificationPreference field suffix
_INAPP_PREF_MAP = {
    'general': 'inapp_general',
    'session': 'inapp_session',
    'booking_confirmed': 'inapp_session',
    'booking_cancelled': 'inapp_session',
    'new_booking': 'inapp_session',
    'session_cancelled_by_host': 'inapp_session',
    'referral': 'inapp_referral',
    'referral_applied': 'inapp_referral',
    'payment': 'inapp_payment',
    'payout': 'inapp_payment',
    'verification': 'inapp_general',
}

_EMAIL_PREF_MAP = {
    'general': 'email_general',
    'session': 'email_session',
    'booking_confirmed': 'email_session',
    'booking_cancelled': 'email_session',
    'new_booking': 'email_session',
    'session_cancelled_by_host': 'email_session',
    'referral': 'email_referral',
    'referral_applied': 'email_referral',
    'payment': 'email_payment',
    'payout': 'email_payment',
    'verification': 'email_general',
}


def send_notification(user=None, notif_type='general', title='', message='', link='',
                      related_object_type='', related_object_id=None, recipient=None):
    """
    Create a Notification record and push it via WebSocket.
    Accepts `user` or `recipient` as the target user (both supported).
    Silently returns None on any error (including Redis being down).
    """
    # Support both `user=` and `recipient=` kwargs
    target_user = user or recipient
    if target_user is None:
        return None
    try:
        if not _check_inapp_preference(target_user, notif_type):
            return None

        from apps.notifications.models import Notification
        notification = Notification.objects.create(
            recipient=target_user,
            notif_type=notif_type,
            title=title,
            message=message,
            link=link,
            related_object_type=related_object_type or '',
            related_object_id=related_object_id,
        )

        _push_to_websocket(target_user.id, notification)

        if _check_email_preference(target_user, notif_type):
            _queue_email(target_user, title, message)

        return notification
    except Exception as exc:
        logger.debug('send_notification silently failed: %s', exc)
        return None


def _check_inapp_preference(user, notif_type):
    """Return True if the user wants in-app notifications for this type."""
    try:
        from apps.notifications.models import NotificationPreference
        pref = NotificationPreference.objects.filter(user=user).first()
        if pref is None:
            return True  # Default: allow
        # Check granular field first, then category field
        granular_map = {
            'general': 'in_app_general',
            'session': 'inapp_session',
            'session_booked': 'in_app_session_booked',
            'booking_confirmed': 'in_app_session_booked',
            'booking_cancelled': 'in_app_session_cancelled',
            'new_booking': 'in_app_session_booked',
            'session_cancelled_by_host': 'in_app_session_cancelled',
            'referral': 'inapp_referral',
            'referral_applied': 'in_app_referral_applied',
            'payment': 'in_app_payment_received',
            'payout': 'in_app_payment_received',
            'verification': 'in_app_general',
        }
        field = granular_map.get(notif_type, 'in_app_general')
        return getattr(pref, field, True)
    except Exception:
        return True


def _check_email_preference(user, notif_type):
    """Return True if the user wants email notifications for this type."""
    try:
        from apps.notifications.models import NotificationPreference
        pref = NotificationPreference.objects.filter(user=user).first()
        if pref is None:
            return False  # Default: no email unless opted in
        field = _EMAIL_PREF_MAP.get(notif_type, 'email_general')
        return getattr(pref, field, False)
    except Exception:
        return False


def _push_to_websocket(user_id, notification):
    """
    Push notification to the user's WebSocket group.
    Silently fails if Redis / channel layer is unavailable.
    """
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        payload = {
            'id': notification.id,
            'notif_type': notification.notif_type,
            'title': notification.title,
            'message': notification.message,
            'link': notification.link,
            'is_read': notification.is_read,
            'created_at': notification.created_at.isoformat(),
        }

        async_to_sync(channel_layer.group_send)(
            f'notifications_user_{user_id}',
            {
                'type': 'notification_message',
                'notification': payload,
            }
        )

        # Also push updated unread count
        push_unread_count(user_id)
    except Exception as exc:
        logger.debug('_push_to_websocket silently failed: %s', exc)


def push_unread_count(user_id):
    """
    Push the current unread count to the user's WebSocket group.
    Silently fails if Redis is down.
    """
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        from apps.notifications.models import Notification

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        count = Notification.objects.filter(recipient_id=user_id, is_read=False).count()

        async_to_sync(channel_layer.group_send)(
            f'notifications_user_{user_id}',
            {
                'type': 'unread_count_update',
                'count': count,
            }
        )
    except Exception as exc:
        logger.debug('push_unread_count silently failed: %s', exc)


def _queue_email(user, title, message):
    """Queue an email notification via Celery task."""
    try:
        from apps.notifications.tasks import send_notification_email
        send_notification_email.delay(user.id, title, message)
    except Exception as exc:
        logger.debug('_queue_email silently failed: %s', exc)
