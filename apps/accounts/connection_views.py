"""
Connection system API views.
Handles: send request, accept/reject, withdraw, list, status check, profile-view stats.
"""
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import Connection, ProfileView

User = get_user_model()


def _send_connection_notification(notif_type, recipient, actor, link=''):
    """Fire a real-time + in-app notification for connection events."""
    try:
        from utils.notify import send_notification
        messages = {
            'connection_request': (
                f'{actor.full_name} sent you a connection request',
                f'{actor.full_name} wants to connect with you on AlumniAI.',
            ),
            'connection_accepted': (
                f'{actor.full_name} accepted your connection request',
                f'You are now connected with {actor.full_name}.',
            ),
        }
        title, message = messages.get(notif_type, ('Connection update', ''))
        send_notification(
            recipient=recipient,
            notif_type=notif_type,
            title=title,
            message=message,
            link=link or f'/{actor.role}/{actor.id}/',
        )
    except Exception:
        pass  # notifications are non-blocking


def _connection_between(user_a, user_b):
    """Return the Connection row between two users (either direction), or None."""
    return Connection.objects.filter(
        Q(requester=user_a, receiver=user_b) |
        Q(requester=user_b, receiver=user_a)
    ).first()


def _serialize_user(user):
    """Minimal user dict for connection lists."""
    pic = user.profile_pic.url if user.profile_pic else None
    role_detail = {}
    try:
        if user.role == 'alumni':
            p = user.alumni_profile
            role_detail = {'company': p.company, 'designation': p.designation}
        elif user.role == 'faculty':
            p = user.faculty_profile
            role_detail = {'department': p.department, 'designation': p.designation}
        elif user.role == 'student':
            p = user.student_profile
            role_detail = {'degree': p.degree, 'branch': p.branch}
    except Exception:
        pass
    return {
        'id': user.id,
        'full_name': user.full_name,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'role': user.role,
        'college': user.college,
        'profile_pic': pic,
        'role_detail': role_detail,
    }


# ── Send connection request ───────────────────────────────────

class SendConnectionView(APIView):
    """POST /api/accounts/connections/request/<user_id>/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        if request.user.id == user_id:
            return Response({'detail': 'You cannot connect with yourself.'}, status=400)

        try:
            receiver = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=404)

        existing = _connection_between(request.user, receiver)
        if existing:
            if existing.status == Connection.STATUS_ACCEPTED:
                return Response({'detail': 'Already connected.'}, status=400)
            if existing.status == Connection.STATUS_PENDING:
                return Response({'detail': 'Connection request already pending.'}, status=400)
            if existing.status == Connection.STATUS_REJECTED:
                # Allow re-requesting after rejection
                existing.delete()

        message = request.data.get('message', '')[:300]
        conn = Connection.objects.create(
            requester=request.user,
            receiver=receiver,
            status=Connection.STATUS_PENDING,
            message=message,
        )

        _send_connection_notification(
            'connection_request', receiver, request.user,
            link=f'/{request.user.role}/{request.user.id}/'
        )

        return Response({
            'connection_id': conn.id,
            'status': 'pending',
            'message': 'Connection request sent.',
        }, status=201)


# ── Respond to connection request ─────────────────────────────

class RespondConnectionView(APIView):
    """POST /api/accounts/connections/<connection_id>/respond/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, connection_id):
        return self._respond(request, connection_id)

    def patch(self, request, connection_id):
        return self._respond(request, connection_id)

    def _respond(self, request, connection_id):
        try:
            conn = Connection.objects.get(id=connection_id, receiver=request.user)
        except Connection.DoesNotExist:
            return Response({'detail': 'Connection request not found.'}, status=404)

        action = request.data.get('action')
        if action not in ('accept', 'reject'):
            return Response({'detail': 'action must be "accept" or "reject".'}, status=400)

        if conn.status != Connection.STATUS_PENDING:
            return Response({'detail': 'This request has already been handled.'}, status=400)

        if action == 'accept':
            conn.status = Connection.STATUS_ACCEPTED
            conn.save(update_fields=['status', 'updated_at'])
            _send_connection_notification(
                'connection_accepted', conn.requester, request.user,
                link=f'/{request.user.role}/{request.user.id}/'
            )
            return Response({'status': 'accepted', 'message': 'Connection accepted.'})
        else:
            conn.status = Connection.STATUS_REJECTED
            conn.save(update_fields=['status', 'updated_at'])
            return Response({'status': 'rejected', 'message': 'Connection declined.'})


# ── Remove / withdraw connection ──────────────────────────────

class RemoveConnectionView(APIView):
    """DELETE /api/accounts/connections/remove/<user_id>/"""
    permission_classes = [IsAuthenticated]

    def delete(self, request, user_id):
        conn = _connection_between(request.user, User(id=user_id))
        # Use real query since User(id=user_id) won't work with Q filter
        conn = Connection.objects.filter(
            Q(requester=request.user, receiver_id=user_id) |
            Q(requester_id=user_id, receiver=request.user)
        ).first()
        if not conn:
            return Response({'detail': 'No connection found.'}, status=404)
        conn.delete()
        return Response({'message': 'Connection removed.'})


# ── Connection status with a specific user ────────────────────

class ConnectionStatusView(APIView):
    """GET /api/accounts/connections/status/<user_id>/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        conn = Connection.objects.filter(
            Q(requester=request.user, receiver_id=user_id) |
            Q(requester_id=user_id, receiver=request.user)
        ).first()

        if not conn:
            return Response({'status': 'none', 'connection_id': None})

        if conn.status == Connection.STATUS_ACCEPTED:
            return Response({'status': 'connected', 'connection_id': conn.id})

        if conn.status == Connection.STATUS_PENDING:
            if conn.requester_id == request.user.id:
                return Response({'status': 'pending_sent', 'connection_id': conn.id})
            else:
                return Response({'status': 'pending_received', 'connection_id': conn.id})

        return Response({'status': 'none', 'connection_id': None})


# ── My connections list ───────────────────────────────────────

class MyConnectionsView(APIView):
    """GET /api/accounts/connections/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        me = request.user

        # Accepted connections (either direction)
        accepted_qs = Connection.objects.filter(
            Q(requester=me) | Q(receiver=me),
            status=Connection.STATUS_ACCEPTED,
        ).select_related('requester', 'requester__alumni_profile',
                         'requester__student_profile', 'requester__faculty_profile',
                         'receiver', 'receiver__alumni_profile',
                         'receiver__student_profile', 'receiver__faculty_profile')

        accepted = []
        for c in accepted_qs:
            other = c.receiver if c.requester_id == me.id else c.requester
            accepted.append({
                'connection_id': c.id,
                'connected_at': c.updated_at.isoformat(),
                'user': _serialize_user(other),
            })

        # Pending received (others sent to me)
        pending_received_qs = Connection.objects.filter(
            receiver=me, status=Connection.STATUS_PENDING
        ).select_related('requester', 'requester__alumni_profile',
                         'requester__student_profile', 'requester__faculty_profile')

        pending_received = [{
            'connection_id': c.id,
            'message': c.message,
            'sent_at': c.created_at.isoformat(),
            'user': _serialize_user(c.requester),
        } for c in pending_received_qs]

        # Pending sent (I sent to others)
        pending_sent_qs = Connection.objects.filter(
            requester=me, status=Connection.STATUS_PENDING
        ).select_related('receiver', 'receiver__alumni_profile',
                         'receiver__student_profile', 'receiver__faculty_profile')

        pending_sent = [{
            'connection_id': c.id,
            'sent_at': c.created_at.isoformat(),
            'user': _serialize_user(c.receiver),
        } for c in pending_sent_qs]

        return Response({
            'accepted': accepted,
            'pending_received': pending_received,
            'pending_sent': pending_sent,
            'counts': {
                'total_connections': len(accepted),
                'pending_received': len(pending_received),
                'pending_sent': len(pending_sent),
            },
        })


# ── Profile view stats ────────────────────────────────────────

class ProfileViewStatsView(APIView):
    """GET /api/accounts/profile-views/stats/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.utils import timezone
        from datetime import timedelta

        me = request.user
        now = timezone.now()

        total_views = ProfileView.objects.filter(profile_owner=me).count()
        views_7d = ProfileView.objects.filter(
            profile_owner=me,
            last_viewed_at__gte=now - timedelta(days=7),
        ).count()
        views_30d = ProfileView.objects.filter(
            profile_owner=me,
            last_viewed_at__gte=now - timedelta(days=30),
        ).count()

        # Recent viewers (last 5 unique)
        recent = ProfileView.objects.filter(
            profile_owner=me
        ).select_related(
            'viewer', 'viewer__alumni_profile',
            'viewer__student_profile', 'viewer__faculty_profile',
        ).order_by('-last_viewed_at')[:5]

        recent_viewers = [{
            'user': _serialize_user(pv.viewer),
            'viewed_at': pv.last_viewed_at.isoformat(),
            'view_count': pv.view_count,
        } for pv in recent]

        # Total connections
        total_connections = Connection.objects.filter(
            Q(requester=me) | Q(receiver=me),
            status=Connection.STATUS_ACCEPTED,
        ).count()

        pending_requests = Connection.objects.filter(
            receiver=me, status=Connection.STATUS_PENDING
        ).count()

        return Response({
            'total_profile_views': total_views,
            'profile_views_7d': views_7d,
            'profile_views_30d': views_30d,
            'recent_viewers': recent_viewers,
            'total_connections': total_connections,
            'pending_connection_requests': pending_requests,
        })
