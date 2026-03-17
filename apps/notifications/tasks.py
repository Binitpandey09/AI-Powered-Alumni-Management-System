from celery import shared_task
from django.utils import timezone
from datetime import timedelta

@shared_task
def cleanup_old_notifications():
    """Delete read notifications older than 30 days"""
    from .models import Notification
    
    cutoff_date = timezone.now() - timedelta(days=30)
    deleted_count = Notification.objects.filter(
        is_read=True,
        created_at__lt=cutoff_date
    ).delete()[0]
    
    return f"Deleted {deleted_count} old notifications"

@shared_task
def send_notification(user_id, notification_type, message, data=None):
    """Create and send notification to user"""
    from .models import Notification
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
    # Create notification
    notification = Notification.objects.create(
        user_id=user_id,
        notification_type=notification_type,
        message=message,
        data=data or {}
    )
    
    # Send via WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'notifications_{user_id}',
        {
            'type': 'notification_message',
            'notification': {
                'id': notification.id,
                'type': notification_type,
                'message': message,
                'created_at': notification.created_at.isoformat(),
            }
        }
    )
    
    return f"Notification sent to user {user_id}"
