from django.utils import timezone
from django.views.generic import TemplateView
from django.shortcuts import redirect
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import Notification, NotificationPreference
from .serializers import NotificationSerializer, NotificationPreferenceSerializer


def _time_ago(dt):
    """Return a human-readable relative time string."""
    now = timezone.now()
    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return 'just now'
    elif seconds < 3600:
        m = seconds // 60
        return f'{m} minute{"s" if m != 1 else ""} ago'
    elif seconds < 86400:
        h = seconds // 3600
        return f'{h} hour{"s" if h != 1 else ""} ago'
    elif seconds < 604800:
        d = seconds // 86400
        return f'{d} day{"s" if d != 1 else ""} ago'
    else:
        return dt.strftime('%b %d, %Y')


class NotificationListView(APIView):
    """GET /api/notifications/ — paginated list with optional ?unread=true filter."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Notification.objects.filter(recipient=request.user)

        unread_only = request.query_params.get('unread', '').lower() == 'true'
        if unread_only:
            qs = qs.filter(is_read=False)

        notif_type = request.query_params.get('type')
        if notif_type:
            qs = qs.filter(notif_type=notif_type)

        # Simple manual pagination
        page = max(1, int(request.query_params.get('page', 1)))
        page_size = 20
        offset = (page - 1) * page_size
        total = qs.count()
        notifications = qs[offset: offset + page_size]

        data = []
        for n in notifications:
            item = NotificationSerializer(n).data
            item['time_ago'] = _time_ago(n.created_at)
            data.append(item)

        return Response({
            'results': data,
            'count': total,
            'total': total,
            'page': page,
            'has_next': (offset + page_size) < total,
            'unread_count': Notification.objects.filter(recipient=request.user, is_read=False).count(),
        })


class NotificationDetailView(APIView):
    """GET /api/notifications/<pk>/ — mark as read on fetch."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            n = Notification.objects.get(pk=pk, recipient=request.user)
        except Notification.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        n.mark_as_read()
        data = NotificationSerializer(n).data
        data['time_ago'] = _time_ago(n.created_at)
        return Response(data)

    def patch(self, request, pk):
        """PATCH /api/notifications/<pk>/ — mark as read."""
        try:
            n = Notification.objects.get(pk=pk, recipient=request.user)
        except Notification.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        n.mark_as_read()
        data = NotificationSerializer(n).data
        data['time_ago'] = _time_ago(n.created_at)
        return Response(data)

    def delete(self, request, pk):
        """DELETE /api/notifications/<pk>/"""
        try:
            n = Notification.objects.get(pk=pk, recipient=request.user)
        except Notification.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        n.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationBulkActionView(APIView):
    """
    POST /api/notifications/bulk/
    Body: { "action": "mark_all_read" | "delete_read" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        action = request.data.get('action')

        if action == 'mark_all_read':
            now = timezone.now()
            updated = Notification.objects.filter(
                recipient=request.user, is_read=False
            ).update(is_read=True, read_at=now)
            return Response({'updated': updated, 'detail': f'Marked {updated} notifications as read.'})

        elif action in ('delete_read', 'delete_all_read'):
            deleted, _ = Notification.objects.filter(
                recipient=request.user, is_read=True
            ).delete()
            return Response({'deleted': deleted, 'detail': f'Deleted {deleted} read notifications.'})

        return Response({'detail': 'Invalid action.'}, status=status.HTTP_400_BAD_REQUEST)


class NotificationUnreadCountView(APIView):
    """GET /api/notifications/unread-count/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({'unread_count': count})


class NotificationPreferenceView(APIView):
    """
    GET  /api/notifications/preferences/  — fetch preferences
    PUT  /api/notifications/preferences/  — update preferences
    """
    permission_classes = [IsAuthenticated]

    def _get_or_create_pref(self, user):
        pref, _ = NotificationPreference.objects.get_or_create(user=user)
        return pref

    def get(self, request):
        pref = self._get_or_create_pref(request.user)
        return Response(NotificationPreferenceSerializer(pref, context={'request': request}).data)

    def put(self, request):
        pref = self._get_or_create_pref(request.user)
        serializer = NotificationPreferenceSerializer(pref, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(NotificationPreferenceSerializer(pref, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        return self.put(request)


# ── Template page views ───────────────────────────────────────────────────────

class NotificationsPageView(TemplateView):
    template_name = 'notifications/notifications_list.html'

    def dispatch(self, request, *args, **kwargs):
        from utils.auth_helpers import get_user_from_token
        token = request.COOKIES.get('access_token')
        user = get_user_from_token(token)
        if not user:
            return redirect('/auth/login/')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['filter_tabs'] = [
            ('All', 'all'), ('Unread', 'unread'), ('Session', 'session'),
            ('Payment', 'payment'), ('Referral', 'referral'), ('General', 'general'),
        ]
        return ctx


class NotificationPreferencesPageView(TemplateView):
    template_name = 'notifications/preferences.html'

    def dispatch(self, request, *args, **kwargs):
        from utils.auth_helpers import get_user_from_token
        token = request.COOKIES.get('access_token')
        user = get_user_from_token(token)
        if not user:
            return redirect('/auth/login/')
        return super().dispatch(request, *args, **kwargs)
