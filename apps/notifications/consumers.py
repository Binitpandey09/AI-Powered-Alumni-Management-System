import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications.
    Expects JWT auth via JWTWebSocketMiddleware (scope['user'] is set before connect).
    Group name: notifications_user_{user_id}
    """

    async def connect(self):
        self.user = self.scope.get('user')

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        self.group_name = f'notifications_user_{self.user.id}'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Send unread count immediately on connect
        count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': count,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """Handle actions sent from the client."""
        try:
            data = json.loads(text_data)
        except (json.JSONDecodeError, TypeError):
            return

        action = data.get('action')

        if action == 'mark_read':
            notification_id = data.get('notification_id')
            if notification_id:
                success = await self.db_mark_read(notification_id)
                if success:
                    count = await self.get_unread_count()
                    await self.send(text_data=json.dumps({
                        'type': 'unread_count',
                        'count': count,
                    }))

        elif action == 'mark_all_read':
            await self.db_mark_all_read()
            await self.send(text_data=json.dumps({
                'type': 'unread_count',
                'count': 0,
            }))

        elif action == 'get_unread_count':
            count = await self.get_unread_count()
            await self.send(text_data=json.dumps({
                'type': 'unread_count',
                'count': count,
            }))

    # ── Event handlers (called by channel layer group_send) ──────────────────

    async def notification_message(self, event):
        """Push a new notification payload to the WebSocket client."""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification'],
        }))

    async def unread_count_update(self, event):
        """Push an updated unread count to the WebSocket client."""
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': event['count'],
        }))

    # ── DB helpers ────────────────────────────────────────────────────────────

    @database_sync_to_async
    def get_unread_count(self):
        from apps.notifications.models import Notification
        return Notification.objects.filter(recipient=self.user, is_read=False).count()

    @database_sync_to_async
    def db_mark_read(self, notification_id):
        from apps.notifications.models import Notification
        try:
            n = Notification.objects.get(pk=notification_id, recipient=self.user)
            n.mark_as_read()
            return True
        except Notification.DoesNotExist:
            return False

    @database_sync_to_async
    def db_mark_all_read(self):
        from apps.notifications.models import Notification
        now = timezone.now()
        Notification.objects.filter(recipient=self.user, is_read=False).update(
            is_read=True,
            read_at=now,
        )
