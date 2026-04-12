from django.shortcuts import redirect
from django.views.generic import TemplateView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Sum, Count, Avg
from decimal import Decimal

from utils.auth_helpers import get_user_from_token


# ── Page view helpers ─────────────────────────────────────────────────────────

class JWTLoginRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        token = request.COOKIES.get('access_token', '')
        user = get_user_from_token(token)
        if not user:
            return redirect(f'/auth/login/?next={request.path}')
        request.user = user
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['user'] = self.request.user
        return ctx


# ── Dashboard page views ──────────────────────────────────────────────────────

class AlumniDashboardView(JWTLoginRequiredMixin, TemplateView):
    template_name = 'dashboard/alumni_dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if hasattr(request, 'user') and request.user.role != 'alumni':
            from utils.auth_helpers import get_dashboard_url
            return redirect(get_dashboard_url(request.user))
        return response


class StudentDashboardView(JWTLoginRequiredMixin, TemplateView):
    template_name = 'dashboard/student_dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if hasattr(request, 'user') and request.user.role != 'student':
            from utils.auth_helpers import get_dashboard_url
            return redirect(get_dashboard_url(request.user))
        return response


class FacultyDashboardView(JWTLoginRequiredMixin, TemplateView):
    template_name = 'dashboard/faculty_dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if hasattr(request, 'user') and request.user.role != 'faculty':
            from utils.auth_helpers import get_dashboard_url
            return redirect(get_dashboard_url(request.user))
        return response


class AdminModerationView(JWTLoginRequiredMixin, TemplateView):
    template_name = 'dashboard/admin_feed_moderation.html'

    def dispatch(self, request, *args, **kwargs):
        token = request.COOKIES.get('access_token', '')
        user = get_user_from_token(token)
        if not user or user.role != 'admin':
            return redirect('/auth/login/')
        request.user = user
        return super(TemplateView, self).dispatch(request, *args, **kwargs)


# ── Admin API Views ───────────────────────────────────────────────────────────

class AdminOverviewView(APIView):
    """GET /api/dashboard/admin/overview/ — platform-wide stats"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Admin only.'}, status=403)

        from django.contrib.auth import get_user_model
        from apps.feed.models import Post
        from apps.sessions_app.models import Session, Booking
        from apps.referrals.models import Referral, ReferralApplication
        from apps.payments.models import Transaction, Wallet, PayoutRequest, AIToolUsage

        User = get_user_model()
        now = timezone.now()

        total_users = User.objects.filter(is_active=True).count()
        total_students = User.objects.filter(role='student', is_active=True).count()
        total_alumni = User.objects.filter(role='alumni', is_active=True).count()
        total_faculty = User.objects.filter(role='faculty', is_active=True).count()
        new_users_today = User.objects.filter(date_joined__date=now.date(), is_active=True).count()
        new_users_this_week = User.objects.filter(
            date_joined__gte=now - timezone.timedelta(days=7), is_active=True
        ).count()

        total_posts = Post.objects.filter(status='active').count()
        flagged_posts = Post.objects.filter(status='flagged').count()
        total_sessions = Session.objects.count()
        upcoming_sessions = Session.objects.filter(status='upcoming').count()
        total_referrals = Referral.objects.filter(status__in=['active', 'closed']).count()
        total_applications = ReferralApplication.objects.count()
        total_hires = ReferralApplication.objects.filter(status='hired').count()

        total_platform_revenue = (
            Transaction.objects.filter(status='completed')
            .aggregate(total=Sum('platform_fee'))['total'] or Decimal('0.00')
        )
        this_month_revenue = (
            Transaction.objects.filter(
                status='completed',
                created_at__year=now.year,
                created_at__month=now.month,
            ).aggregate(total=Sum('platform_fee'))['total'] or Decimal('0.00')
        )
        pending_payouts = (
            PayoutRequest.objects.filter(status__in=['pending', 'approved'])
            .aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        )
        pending_payout_count = PayoutRequest.objects.filter(status='pending').count()

        pending_verification = 0
        try:
            from apps.accounts.models import AlumniProfile
            pending_verification = AlumniProfile.objects.filter(
                verification_status='pending'
            ).count()
        except Exception:
            pass

        total_ai_usages = AIToolUsage.objects.count()
        ai_revenue = (
            Transaction.objects.filter(
                status='completed',
                transaction_type__in=['resume_check', 'resume_builder', 'ai_interview', 'skill_gap'],
            ).aggregate(total=Sum('gross_amount'))['total'] or Decimal('0.00')
        )

        signups_chart = []
        for i in range(6, -1, -1):
            day = (now - timezone.timedelta(days=i)).date()
            count = User.objects.filter(date_joined__date=day, is_active=True).count()
            signups_chart.append({'date': str(day), 'day': day.strftime('%a'), 'count': count})

        revenue_chart = []
        for i in range(5, -1, -1):
            m_date = now.replace(day=1)
            for _ in range(i):
                if m_date.month == 1:
                    m_date = m_date.replace(year=m_date.year - 1, month=12)
                else:
                    m_date = m_date.replace(month=m_date.month - 1)
            m_rev = (
                Transaction.objects.filter(
                    status='completed',
                    created_at__year=m_date.year,
                    created_at__month=m_date.month,
                ).aggregate(total=Sum('platform_fee'))['total'] or Decimal('0.00')
            )
            revenue_chart.append({'month': m_date.strftime('%b'), 'revenue': float(m_rev)})

        return Response({
            'users': {
                'total': total_users,
                'students': total_students,
                'alumni': total_alumni,
                'faculty': total_faculty,
                'new_today': new_users_today,
                'new_this_week': new_users_this_week,
            },
            'content': {
                'total_posts': total_posts,
                'flagged_posts': flagged_posts,
                'total_sessions': total_sessions,
                'upcoming_sessions': upcoming_sessions,
                'total_referrals': total_referrals,
                'total_applications': total_applications,
                'total_hires': total_hires,
            },
            'financial': {
                'total_platform_revenue': str(total_platform_revenue),
                'this_month_revenue': str(this_month_revenue),
                'pending_payouts': str(pending_payouts),
                'pending_payout_count': pending_payout_count,
            },
            'verification': {
                'pending_alumni_verification': pending_verification,
            },
            'ai_tools': {
                'total_usages': total_ai_usages,
                'total_revenue': str(ai_revenue),
            },
            'charts': {
                'signups_last_7_days': signups_chart,
                'revenue_last_6_months': revenue_chart,
            },
        })


class AdminUserListView(APIView):
    """GET /api/dashboard/admin/users/ — paginated user list with filters"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Admin only.'}, status=403)

        from django.contrib.auth import get_user_model
        User = get_user_model()

        qs = User.objects.all().order_by('-date_joined')

        role_filter = request.query_params.get('role')
        if role_filter:
            qs = qs.filter(role=role_filter)

        is_active = request.query_params.get('is_active')
        if is_active == 'true':
            qs = qs.filter(is_active=True)
        elif is_active == 'false':
            qs = qs.filter(is_active=False)

        is_suspended = request.query_params.get('is_suspended')
        if is_suspended == 'true':
            qs = qs.filter(is_suspended=True)

        verified_filter = request.query_params.get('is_verified')
        if verified_filter == 'true':
            qs = qs.filter(is_verified=True)
        elif verified_filter == 'false':
            qs = qs.filter(is_verified=False)

        search = request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(college__icontains=search)
            )

        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(qs, request)

        data = []
        for user in page:
            user_data = {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'is_active': user.is_active,
                'is_verified': user.is_verified,
                'is_suspended': getattr(user, 'is_suspended', False),
                'college': getattr(user, 'college', ''),
                'date_joined': user.date_joined.isoformat(),
                'profile_pic': user.profile_pic.url if user.profile_pic else None,
            }
            if user.role == 'alumni':
                try:
                    p = user.alumni_profile
                    user_data['company'] = p.company
                    user_data['designation'] = p.designation
                    user_data['verification_status'] = p.verification_status
                    user_data['wallet_balance'] = str(p.wallet_balance or 0)
                except Exception:
                    pass
            elif user.role == 'student':
                try:
                    p = user.student_profile
                    user_data['skills_count'] = len(p.skills or [])
                    user_data['profile_completeness'] = p.profile_completeness_score
                except Exception:
                    pass
            data.append(user_data)

        return paginator.get_paginated_response(data)


class AdminUserActionView(APIView):
    """POST /api/dashboard/admin/users/{user_id}/action/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        if request.user.role != 'admin':
            return Response({'error': 'Admin only.'}, status=403)

        from django.contrib.auth import get_user_model
        from apps.accounts.models import AdminActionLog
        User = get_user_model()

        target_user = get_object_or_404(User, pk=user_id)
        action = request.data.get('action')
        note = request.data.get('note', '').strip()

        if action == 'suspend':
            if target_user.role == 'admin':
                return Response({'error': 'Cannot suspend admin users.'}, status=400)
            target_user.is_suspended = True
            target_user.suspended_reason = note
            target_user.suspended_at = timezone.now()
            target_user.save(update_fields=['is_suspended', 'suspended_reason', 'suspended_at'])
            log_action = 'user_suspended'

        elif action == 'unsuspend':
            target_user.is_suspended = False
            target_user.suspended_reason = ''
            target_user.save(update_fields=['is_suspended', 'suspended_reason'])
            log_action = 'user_unsuspended'

        elif action == 'delete':
            if target_user.role == 'admin':
                return Response({'error': 'Cannot delete admin users.'}, status=400)
            target_user.is_active = False
            target_user.save(update_fields=['is_active'])
            log_action = 'user_deleted'

        elif action == 'restore':
            target_user.is_active = True
            target_user.save(update_fields=['is_active'])
            log_action = 'user_unsuspended'

        elif action == 'verify':
            target_user.is_verified = True
            target_user.save(update_fields=['is_verified'])
            log_action = 'user_verified'

        else:
            return Response(
                {'error': 'Invalid action. Use: suspend, unsuspend, delete, restore, verify'},
                status=400,
            )

        AdminActionLog.objects.create(
            admin=request.user,
            action_type=log_action,
            target_user=target_user,
            note=note,
        )
        return Response({'message': f'User {action} successful.', 'user_id': user_id})


class AdminAlumniVerificationView(APIView):
    """
    GET  /api/dashboard/admin/alumni/verification/       — list pending alumni
    POST /api/dashboard/admin/alumni/verification/{id}/  — approve or reject
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Admin only.'}, status=403)

        from apps.accounts.models import AlumniProfile
        status_filter = request.query_params.get('status', 'pending')
        profiles = (
            AlumniProfile.objects
            .filter(verification_status=status_filter)
            .select_related('user')
            .order_by('-user__date_joined')
        )
        data = []
        for p in profiles:
            data.append({
                'alumni_id': p.user.id,
                'profile_id': p.id,
                'name': f"{p.user.first_name} {p.user.last_name}".strip(),
                'email': p.user.email,
                'company': p.company,
                'designation': p.designation,
                'verification_status': p.verification_status,
                'verification_document_url': p.verification_document_url,
                'verification_note': p.verification_note,
                'joined': p.user.date_joined.isoformat(),
                'profile_pic': p.user.profile_pic.url if p.user.profile_pic else None,
            })
        return Response({'alumni': data, 'count': len(data)})

    def post(self, request, alumni_id):
        if request.user.role != 'admin':
            return Response({'error': 'Admin only.'}, status=403)

        from apps.accounts.models import AlumniProfile, AdminActionLog
        from django.contrib.auth import get_user_model
        User = get_user_model()

        alumni_user = get_object_or_404(User, pk=alumni_id, role='alumni')
        try:
            profile = alumni_user.alumni_profile
        except Exception:
            return Response({'error': 'Alumni profile not found.'}, status=404)

        action = request.data.get('action')
        note = request.data.get('note', '').strip()

        if action == 'approve':
            profile.verification_status = 'verified'
            profile.is_verified = True
            profile.verified_at = timezone.now()
            profile.verified_by = request.user
            profile.verification_note = note
            profile.save(update_fields=[
                'verification_status', 'is_verified', 'verified_at',
                'verified_by', 'verification_note',
            ])
            alumni_user.is_verified = True
            alumni_user.save(update_fields=['is_verified'])
            log_action = 'alumni_verified'
            try:
                from apps.notifications.models import Notification
                Notification.objects.create(
                    recipient=alumni_user,
                    notif_type='general',
                    title='Profile Verified!',
                    message='Your alumni profile has been verified. You can now post referrals and host sessions.',
                    link='/dashboard/alumni/',
                )
            except Exception:
                pass

        elif action == 'reject':
            if not note:
                return Response({'error': 'Rejection reason (note) is required.'}, status=400)
            profile.verification_status = 'rejected'
            profile.verification_note = note
            profile.save(update_fields=['verification_status', 'verification_note'])
            log_action = 'alumni_rejected'
            try:
                from apps.notifications.models import Notification
                Notification.objects.create(
                    recipient=alumni_user,
                    notif_type='general',
                    title='Verification Update',
                    message=f'Your alumni verification was not approved. Reason: {note}',
                    link='/dashboard/alumni/',
                )
            except Exception:
                pass

        else:
            return Response({'error': 'action must be approve or reject'}, status=400)

        AdminActionLog.objects.create(
            admin=request.user,
            action_type=log_action,
            target_user=alumni_user,
            note=note,
        )
        return Response({'message': f'Alumni verification {action}d successfully.'})


class AdminContentModerationView(APIView):
    """
    GET  /api/dashboard/admin/moderation/ — flagged content
    POST /api/dashboard/admin/moderation/ — take action on content
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Admin only.'}, status=403)

        content_type = request.query_params.get('type', 'all')
        data = {'flagged_posts': [], 'reported_sessions': [], 'flagged_referrals': []}

        if content_type in ['all', 'posts']:
            try:
                from apps.feed.models import Post
                flagged_posts = (
                    Post.objects
                    .filter(status__in=['flagged', 'active'])
                    .filter(flagged_count__gt=0)
                    .select_related('author')
                    .order_by('-flagged_count')[:20]
                )
                data['flagged_posts'] = [
                    {
                        'id': p.id,
                        'author_name': f"{p.author.first_name} {p.author.last_name}".strip(),
                        'author_email': p.author.email,
                        'post_type': p.post_type,
                        'content_preview': p.content[:200],
                        'flagged_count': p.flagged_count,
                        'status': p.status,
                        'created_at': p.created_at.isoformat(),
                    }
                    for p in flagged_posts
                ]
            except Exception:
                pass

        if content_type in ['all', 'referrals']:
            try:
                from apps.referrals.models import Referral
                flagged_referrals = (
                    Referral.objects.filter(status='active').order_by('-created_at')[:10]
                )
                data['flagged_referrals'] = [
                    {
                        'id': r.id,
                        'job_title': r.job_title,
                        'company_name': r.company_name,
                        'posted_by': r.posted_by.email,
                        'status': r.status,
                        'total_applications': r.total_applications,
                        'created_at': r.created_at.isoformat(),
                    }
                    for r in flagged_referrals
                ]
            except Exception:
                pass

        return Response(data)

    def post(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Admin only.'}, status=403)

        from apps.accounts.models import AdminActionLog
        content_type = request.data.get('content_type')
        object_id = request.data.get('object_id')
        action = request.data.get('action')
        note = request.data.get('note', '')

        if content_type == 'post':
            from apps.feed.models import Post
            post = get_object_or_404(Post, pk=object_id)
            if action == 'approve':
                post.status = 'active'
                post.flagged_count = 0
            elif action == 'hide':
                post.status = 'hidden'
            elif action == 'delete':
                post.status = 'deleted'
            post.admin_note = note
            post.save()
            log_action = 'post_approved' if action == 'approve' else f'post_{action}d'
            AdminActionLog.objects.create(
                admin=request.user, action_type=log_action,
                target_object_type='post', target_object_id=object_id, note=note,
            )

        elif content_type == 'referral':
            from apps.referrals.models import Referral
            referral = get_object_or_404(Referral, pk=object_id)
            if action == 'deactivate':
                referral.status = 'deactivated'
                referral.admin_note = note
                referral.save()
            AdminActionLog.objects.create(
                admin=request.user, action_type='referral_deactivated',
                target_object_type='referral', target_object_id=object_id, note=note,
            )

        elif content_type == 'session':
            from apps.sessions_app.models import Session
            session = get_object_or_404(Session, pk=object_id)
            if action == 'cancel':
                session.status = 'cancelled'
                session.cancellation_reason = note
                session.save()
            AdminActionLog.objects.create(
                admin=request.user, action_type='session_cancelled',
                target_object_type='session', target_object_id=object_id, note=note,
            )

        else:
            return Response({'error': 'Invalid content_type.'}, status=400)

        return Response({'message': f'{content_type} {action} action completed.'})


class AdminSessionsView(APIView):
    """GET /api/dashboard/admin/sessions/ — all sessions for admin review"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Admin only.'}, status=403)

        from apps.sessions_app.models import Session
        qs = Session.objects.select_related('host').order_by('-created_at')

        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        search = request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(title__icontains=search) | Q(host__email__icontains=search)
            )

        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(qs, request)

        data = [
            {
                'id': s.id,
                'title': s.title,
                'host_name': f"{s.host.first_name} {s.host.last_name}".strip(),
                'host_email': s.host.email,
                'session_type': s.session_type,
                'status': s.status,
                'scheduled_at': s.scheduled_at.isoformat(),
                'price': str(s.price),
                'booked_seats': s.booked_seats,
                'max_seats': s.max_seats,
                'total_revenue': str(s.total_revenue),
            }
            for s in page
        ]
        return paginator.get_paginated_response(data)


class AdminBroadcastView(APIView):
    """POST /api/dashboard/admin/broadcast/ — send notification to all or specific role"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Admin only.'}, status=403)

        title = request.data.get('title', '').strip()
        message = request.data.get('message', '').strip()
        target_role = request.data.get('target_role', 'all')
        link = request.data.get('link', '').strip()

        if not title or not message:
            return Response({'error': 'title and message are required.'}, status=400)

        from django.contrib.auth import get_user_model
        from apps.notifications.models import Notification
        from apps.accounts.models import AdminActionLog
        User = get_user_model()

        if target_role == 'all':
            recipients = User.objects.filter(is_active=True).exclude(role='admin')
        else:
            recipients = User.objects.filter(role=target_role, is_active=True)

        count = 0
        for user in recipients:
            try:
                Notification.objects.create(
                    recipient=user,
                    notif_type='general',
                    title=title,
                    message=message,
                    link=link or '/',
                )
                count += 1
            except Exception:
                pass

        AdminActionLog.objects.create(
            admin=request.user,
            action_type='broadcast_sent',
            note=f'Sent to {target_role}: {title}',
        )
        return Response({'message': f'Broadcast sent to {count} users.', 'count': count})


class AdminReferralsView(APIView):
    """GET /api/dashboard/admin/referrals/ — all referrals for admin review"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Admin only.'}, status=403)

        from apps.referrals.models import Referral
        qs = Referral.objects.select_related('posted_by').order_by('-created_at')

        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        search = request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(job_title__icontains=search) |
                Q(company_name__icontains=search) |
                Q(posted_by__email__icontains=search)
            )

        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(qs, request)

        data = [
            {
                'id': r.id,
                'job_title': r.job_title,
                'company_name': r.company_name,
                'posted_by_name': f"{r.posted_by.first_name} {r.posted_by.last_name}".strip(),
                'posted_by_email': r.posted_by.email,
                'work_type': r.work_type,
                'status': r.status,
                'total_applications': r.total_applications,
                'max_applicants': r.max_applicants,
                'deadline': r.deadline.isoformat(),
                'is_boosted': r.is_boosted,
                'created_at': r.created_at.isoformat(),
            }
            for r in page
        ]
        return paginator.get_paginated_response(data)


class AdminActionLogView(APIView):
    """GET /api/dashboard/admin/action-log/ — audit trail"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Admin only.'}, status=403)

        from apps.accounts.models import AdminActionLog
        qs = AdminActionLog.objects.select_related('admin', 'target_user').order_by('-created_at')

        action_type = request.query_params.get('action_type')
        if action_type:
            qs = qs.filter(action_type=action_type)

        paginator = PageNumberPagination()
        paginator.page_size = 50
        page = paginator.paginate_queryset(qs, request)

        data = [
            {
                'id': log.id,
                'admin_name': (
                    f"{log.admin.first_name} {log.admin.last_name}".strip()
                    if log.admin else 'System'
                ),
                'action_type': log.action_type,
                'action_display': log.get_action_type_display(),
                'target_user_email': log.target_user.email if log.target_user else None,
                'target_object_type': log.target_object_type,
                'target_object_id': log.target_object_id,
                'note': log.note,
                'created_at': log.created_at.isoformat(),
            }
            for log in page
        ]
        return paginator.get_paginated_response(data)


# ── Admin Panel Page Views ────────────────────────────────────────────────────

class AdminBasePageMixin:
    """Mixin for all admin panel page views — validates JWT and enforces admin role."""

    def dispatch(self, request, *args, **kwargs):
        import logging
        logger = logging.getLogger('admin_access')
        token = request.COOKIES.get('access_token', '')
        user = get_user_from_token(token)
        if not user or user.role != 'admin':
            return redirect('/auth/login/?next=' + request.path)
        logger.info(f'Admin panel accessed by {user.email} from {request.META.get("REMOTE_ADDR")}')
        request.user = user
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['user'] = self.request.user
        return ctx


class AdminDashboardPageView(AdminBasePageMixin, TemplateView):
    template_name = 'admin_panel/dashboard.html'


class AdminUsersPageView(AdminBasePageMixin, TemplateView):
    template_name = 'admin_panel/users.html'


class AdminAlumniVerificationPageView(AdminBasePageMixin, TemplateView):
    template_name = 'admin_panel/alumni_verification.html'


class AdminModerationPageView(AdminBasePageMixin, TemplateView):
    template_name = 'admin_panel/moderation.html'


class AdminSessionsPageView(AdminBasePageMixin, TemplateView):
    template_name = 'admin_panel/sessions.html'


class AdminReferralsPageView(AdminBasePageMixin, TemplateView):
    template_name = 'admin_panel/referrals.html'


class AdminRevenuePageView(AdminBasePageMixin, TemplateView):
    template_name = 'admin_panel/revenue.html'


class AdminPayoutsPageView(AdminBasePageMixin, TemplateView):
    template_name = 'admin_panel/payouts.html'


class AdminAIUsagePageView(AdminBasePageMixin, TemplateView):
    template_name = 'admin_panel/ai_usage.html'


class AdminBroadcastPageView(AdminBasePageMixin, TemplateView):
    template_name = 'admin_panel/broadcast.html'


class AdminAuditLogPageView(AdminBasePageMixin, TemplateView):
    template_name = 'admin_panel/audit_log.html'


# ── Dashboard API Views ────────────────────────────────────────────────────────

class StudentDashboardDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'student':
            return Response({'error': 'Student only.'}, status=403)

        user = request.user
        from django.utils import timezone
        from django.db.models import Avg

        # ── Profile data ──
        profile_score = 0
        skills = []
        try:
            sp = user.student_profile
            profile_score = sp.profile_completeness_score or 0
            skills = sp.skills or []
        except Exception:
            pass

        # ── Session stats ──
        from apps.sessions_app.models import Booking, Session
        total_bookings = Booking.objects.filter(student=user).count()
        attended = Booking.objects.filter(student=user, status='completed').count()
        upcoming_bookings = Booking.objects.filter(
            student=user,
            status='confirmed',
            session__scheduled_at__gte=timezone.now()
        ).select_related('session', 'session__host').order_by('session__scheduled_at')[:5]

        upcoming_sessions_data = [{
            'booking_id': b.id,
            'session_id': b.session.id,
            'title': b.session.title,
            'session_type': b.session.session_type,
            'host_name': f"{b.session.host.first_name} {b.session.host.last_name}".strip(),
            'scheduled_at': b.session.scheduled_at.isoformat(),
            'duration_minutes': b.session.duration_minutes,
        } for b in upcoming_bookings]

        # ── Referral stats ──
        from apps.referrals.models import ReferralApplication, Referral
        total_applied = ReferralApplication.objects.filter(
            student=user
        ).exclude(status='withdrawn').count()
        shortlisted = ReferralApplication.objects.filter(
            student=user, status='shortlisted'
        ).count()
        hired = ReferralApplication.objects.filter(
            student=user, status='hired'
        ).count()

        recent_applications = ReferralApplication.objects.filter(
            student=user
        ).exclude(status='withdrawn').select_related(
            'referral', 'referral__posted_by'
        ).order_by('-applied_at')[:5]

        applications_data = [{
            'application_id': a.id,
            'referral_id': a.referral.id,
            'job_title': a.referral.job_title,
            'company_name': a.referral.company_name,
            'status': a.status,
            'match_score': a.match_score,
            'applied_at': a.applied_at.isoformat(),
        } for a in recent_applications]

        # ── AI tools stats ──
        from apps.payments.models import AIToolUsage
        ai_total_uses = AIToolUsage.objects.filter(user=user).count()
        last_resume_check = AIToolUsage.objects.filter(
            user=user, tool_type='resume_check'
        ).exclude(result_data={}).order_by('-created_at').first()
        last_skill_gap = AIToolUsage.objects.filter(
            user=user, tool_type='skill_gap'
        ).exclude(result_data={}).order_by('-created_at').first()
        last_interview = AIToolUsage.objects.filter(
            user=user, tool_type='ai_interview'
        ).exclude(result_data={}).order_by('-created_at').first()
        resume_check_free = AIToolUsage.get_free_uses_remaining(user, 'resume_check')

        ai_data = {
            'total_uses': ai_total_uses,
            'resume_check': {
                'count': AIToolUsage.objects.filter(user=user, tool_type='resume_check').count(),
                'last_score': last_resume_check.result_data.get('overall_score') if last_resume_check else None,
                'last_grade': last_resume_check.result_data.get('grade') if last_resume_check else None,
                'free_remaining': resume_check_free,
            },
            'skill_gap': {
                'count': AIToolUsage.objects.filter(user=user, tool_type='skill_gap').count(),
                'last_readiness': last_skill_gap.result_data.get('readiness_score') if last_skill_gap else None,
                'last_role': last_skill_gap.result_data.get('target_role') if last_skill_gap else None,
            },
            'ai_interview': {
                'count': AIToolUsage.objects.filter(user=user, tool_type='ai_interview').count(),
                'last_score': last_interview.result_data.get('final_report', {}).get('overall_score') if last_interview else None,
                'last_recommendation': last_interview.result_data.get('final_report', {}).get('hiring_recommendation') if last_interview else None,
            },
            'resume_builder': {
                'count': AIToolUsage.objects.filter(user=user, tool_type='resume_builder').count(),
            },
        }

        # ── Top referrals by match score ──
        from utils.skill_matcher import calculate_skill_match
        active_referrals = Referral.objects.filter(status='active').select_related(
            'posted_by'
        ).order_by('-created_at')[:20]

        matched_referrals = []
        for r in active_referrals:
            result = calculate_skill_match(skills, r.required_skills, r.preferred_skills)
            matched_referrals.append({
                'referral_id': r.id,
                'job_title': r.job_title,
                'company_name': r.company_name,
                'work_type': r.work_type,
                'match_score': result['score'],
                'slots_remaining': r.slots_remaining,
                'deadline': r.deadline.isoformat(),
                'is_urgent': r.is_urgent,
            })
        matched_referrals.sort(key=lambda x: -x['match_score'])
        top_referrals = matched_referrals[:4]

        # ── Recent feed posts ──
        from apps.feed.models import Post
        recent_posts = Post.objects.filter(
            status='active'
        ).select_related('author').order_by('-created_at')[:4]
        posts_data = [{
            'post_id': p.id,
            'author_name': f"{p.author.first_name} {p.author.last_name}".strip(),
            'post_type': p.post_type,
            'content_preview': p.content[:120],
            'likes_count': p.likes_count,
            'comments_count': p.comments_count,
            'created_at': p.created_at.isoformat(),
        } for p in recent_posts]

        # ── Alumni to connect with ──
        from django.contrib.auth import get_user_model
        User = get_user_model()
        alumni_to_connect = User.objects.filter(
            role='alumni', is_active=True, is_verified=True
        ).select_related('alumni_profile').order_by('-alumni_profile__impact_score')[:4]
        connect_data = [{
            'user_id': a.id,
            'name': f"{a.first_name} {a.last_name}".strip(),
            'company': getattr(a.alumni_profile, 'company', ''),
            'designation': getattr(a.alumni_profile, 'designation', ''),
            'impact_score': getattr(a.alumni_profile, 'impact_score', 0),
            'profile_pic': a.profile_pic.url if a.profile_pic else None,
        } for a in alumni_to_connect]

        # ── Notifications unread count ──
        from apps.notifications.models import Notification
        unread_notifs = Notification.objects.filter(recipient=user, is_read=False).count()

        return Response({
            'profile': {
                'score': profile_score,
                'skills_count': len(skills),
                'name': f"{user.first_name} {user.last_name}".strip(),
            },
            'sessions': {
                'total_booked': total_bookings,
                'attended': attended,
                'upcoming': upcoming_sessions_data,
            },
            'referrals': {
                'total_applied': total_applied,
                'shortlisted': shortlisted,
                'hired': hired,
                'recent_applications': applications_data,
            },
            'ai_tools': ai_data,
            'top_referrals_for_you': top_referrals,
            'recent_feed_posts': posts_data,
            'alumni_to_connect': connect_data,
            'unread_notifications': unread_notifs,
        })


class AlumniDashboardDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'alumni':
            return Response({'error': 'Alumni only.'}, status=403)

        user = request.user
        from django.utils import timezone
        from django.db.models import Sum, Avg

        # ── Wallet data ──
        from apps.payments.models import Wallet, PayoutRequest, Transaction
        wallet = None
        wallet_data = {'balance': '0.00', 'total_earned': '0.00', 'pending_withdrawal': '0.00', 'can_withdraw': False}
        try:
            wallet = user.wallet
            wallet_data = {
                'balance': str(wallet.balance),
                'total_earned': str(wallet.total_earned),
                'pending_withdrawal': str(wallet.pending_withdrawal),
                'can_withdraw': wallet.can_withdraw,
            }
        except Exception:
            pass

        # ── This month earnings ──
        now = timezone.now()
        this_month_earned = Transaction.objects.filter(
            payee=user,
            status='completed',
            created_at__year=now.year,
            created_at__month=now.month,
        ).aggregate(total=Sum('payee_amount'))['total'] or 0

        # ── Session stats ──
        from apps.sessions_app.models import Session, Booking, SessionReview
        total_sessions = Session.objects.filter(host=user).count()
        upcoming_sessions = Session.objects.filter(
            host=user, status='upcoming',
            scheduled_at__gte=timezone.now()
        ).order_by('scheduled_at')

        total_students = Booking.objects.filter(
            session__host=user, status='confirmed'
        ).values('student').distinct().count()

        upcoming_data = [{
            'session_id': s.id,
            'title': s.title,
            'session_type': s.session_type,
            'scheduled_at': s.scheduled_at.isoformat(),
            'booked_seats': s.booked_seats,
            'max_seats': s.max_seats,
            'price': str(s.price),
        } for s in upcoming_sessions[:5]]

        # ── Session reviews ──
        recent_reviews = SessionReview.objects.filter(
            session__host=user
        ).select_related('student', 'session').order_by('-created_at')[:3]
        avg_rating = SessionReview.objects.filter(
            session__host=user
        ).aggregate(avg=Avg('rating'))['avg'] or 0

        reviews_data = [{
            'student_name': f"{r.student.first_name} {r.student.last_name}".strip(),
            'rating': r.rating,
            'comment': r.comment[:100] if r.comment else '',
            'session_title': r.session.title,
        } for r in recent_reviews]

        # ── Referral stats ──
        from apps.referrals.models import Referral, ReferralApplication, ReferralSuccessStory
        active_referrals = Referral.objects.filter(
            posted_by=user, status='active'
        ).order_by('-created_at')
        total_referrals = Referral.objects.filter(posted_by=user).count()
        total_applications_received = ReferralApplication.objects.filter(
            referral__posted_by=user
        ).count()
        total_placements = ReferralSuccessStory.objects.filter(alumni=user).count()

        referrals_data = [{
            'referral_id': r.id,
            'job_title': r.job_title,
            'company_name': r.company_name,
            'total_applications': r.total_applications,
            'slots_remaining': r.slots_remaining,
            'deadline': r.deadline.isoformat(),
            'status': r.status,
        } for r in active_referrals[:4]]

        # ── Recent applications received ──
        recent_apps = ReferralApplication.objects.filter(
            referral__posted_by=user
        ).select_related('student', 'referral').order_by('-applied_at')[:5]
        apps_data = [{
            'application_id': a.id,
            'student_name': f"{a.student.first_name} {a.student.last_name}".strip(),
            'referral_title': a.referral.job_title,
            'company': a.referral.company_name,
            'match_score': a.match_score,
            'status': a.status,
            'applied_at': a.applied_at.isoformat(),
        } for a in recent_apps]

        # ── Monthly earnings chart ──
        monthly_earnings = []
        for i in range(5, -1, -1):
            m_date = now.replace(day=1)
            for _ in range(i):
                if m_date.month == 1:
                    m_date = m_date.replace(year=m_date.year - 1, month=12)
                else:
                    m_date = m_date.replace(month=m_date.month - 1)
            earned = Transaction.objects.filter(
                payee=user,
                status='completed',
                created_at__year=m_date.year,
                created_at__month=m_date.month,
            ).aggregate(total=Sum('payee_amount'))['total'] or 0
            monthly_earnings.append({
                'month': m_date.strftime('%b'),
                'earned': float(earned),
            })

        # ── Profile verification ──
        verification_status = 'not_submitted'
        try:
            verification_status = user.alumni_profile.verification_status
        except Exception:
            pass

        impact_score = 0
        try:
            impact_score = user.alumni_profile.impact_score or 0
        except Exception:
            pass

        return Response({
            'wallet': wallet_data,
            'this_month_earned': str(this_month_earned),
            'sessions': {
                'total': total_sessions,
                'upcoming_count': upcoming_sessions.count(),
                'total_students_helped': total_students,
                'upcoming': upcoming_data,
                'avg_rating': round(float(avg_rating), 1),
                'recent_reviews': reviews_data,
            },
            'referrals': {
                'total': total_referrals,
                'total_applications_received': total_applications_received,
                'total_placements': total_placements,
                'active_referrals': referrals_data,
                'recent_applications': apps_data,
            },
            'monthly_earnings': monthly_earnings,
            'verification_status': verification_status,
            'impact_score': impact_score,
        })


class FacultyDashboardDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'faculty':
            return Response({'error': 'Faculty only.'}, status=403)

        user = request.user
        from django.utils import timezone
        from django.db.models import Sum, Avg

        # ── Wallet ──
        from apps.payments.models import Wallet, Transaction
        wallet_data = {'balance': '0.00', 'total_earned': '0.00', 'can_withdraw': False}
        try:
            w = user.wallet
            wallet_data = {
                'balance': str(w.balance),
                'total_earned': str(w.total_earned),
                'can_withdraw': w.can_withdraw,
            }
        except Exception:
            pass

        now = timezone.now()
        this_month_earned = Transaction.objects.filter(
            payee=user,
            status='completed',
            created_at__year=now.year,
            created_at__month=now.month,
        ).aggregate(total=Sum('payee_amount'))['total'] or 0

        # ── Sessions ──
        from apps.sessions_app.models import Session, Booking, SessionReview
        total_sessions = Session.objects.filter(host=user).count()
        upcoming_sessions = Session.objects.filter(
            host=user, status='upcoming',
            scheduled_at__gte=timezone.now()
        ).order_by('scheduled_at')[:5]

        total_students = Booking.objects.filter(
            session__host=user, status='confirmed'
        ).values('student').distinct().count()

        upcoming_data = [{
            'session_id': s.id,
            'title': s.title,
            'session_type': s.session_type,
            'scheduled_at': s.scheduled_at.isoformat(),
            'booked_seats': s.booked_seats,
            'max_seats': s.max_seats,
        } for s in upcoming_sessions]

        avg_rating = SessionReview.objects.filter(
            session__host=user
        ).aggregate(avg=Avg('rating'))['avg'] or 0

        recent_reviews = SessionReview.objects.filter(
            session__host=user
        ).select_related('student', 'session').order_by('-created_at')[:3]
        reviews_data = [{
            'student_name': f"{r.student.first_name} {r.student.last_name}".strip(),
            'rating': r.rating,
            'comment': r.comment[:100] if r.comment else '',
            'session_title': r.session.title,
        } for r in recent_reviews]

        # ── Recommendations ──
        from apps.referrals.models import FacultyReferralRecommendation, ReferralApplication
        recommendations_made = FacultyReferralRecommendation.objects.filter(
            faculty=user
        ).select_related('student', 'referral').order_by('-created_at')[:5]

        recs_data = []
        for rec in recommendations_made:
            application_status = 'not_applied'
            try:
                app = ReferralApplication.objects.get(
                    referral=rec.referral, student=rec.student
                )
                application_status = app.status
            except ReferralApplication.DoesNotExist:
                pass
            recs_data.append({
                'student_name': f"{rec.student.first_name} {rec.student.last_name}".strip(),
                'referral_title': rec.referral.job_title,
                'company': rec.referral.company_name,
                'referral_id': rec.referral.id,
                'student_id': rec.student.id,
                'status': application_status,
                'recommended_at': rec.created_at.isoformat(),
            })

        # ── Top students to recommend ──
        from django.contrib.auth import get_user_model
        User = get_user_model()
        top_students = User.objects.filter(
            role='student', is_active=True, is_verified=True
        ).select_related('student_profile').order_by(
            '-student_profile__profile_completeness_score'
        )[:5]
        students_data = [{
            'user_id': s.id,
            'name': f"{s.first_name} {s.last_name}".strip(),
            'college': getattr(s, 'college', ''),
            'skills': getattr(s.student_profile, 'skills', [])[:4],
            'profile_score': getattr(s.student_profile, 'profile_completeness_score', 0),
        } for s in top_students]

        # ── Monthly earnings chart ──
        monthly_earnings = []
        for i in range(5, -1, -1):
            m_date = now.replace(day=1)
            for _ in range(i):
                if m_date.month == 1:
                    m_date = m_date.replace(year=m_date.year - 1, month=12)
                else:
                    m_date = m_date.replace(month=m_date.month - 1)
            earned = Transaction.objects.filter(
                payee=user,
                status='completed',
                created_at__year=m_date.year,
                created_at__month=m_date.month,
            ).aggregate(total=Sum('payee_amount'))['total'] or 0
            monthly_earnings.append({
                'month': m_date.strftime('%b'),
                'earned': float(earned),
            })

        return Response({
            'wallet': wallet_data,
            'this_month_earned': str(this_month_earned),
            'sessions': {
                'total': total_sessions,
                'upcoming_count': len(upcoming_data),
                'total_students_mentored': total_students,
                'upcoming': upcoming_data,
                'avg_rating': round(float(avg_rating), 1),
                'recent_reviews': reviews_data,
            },
            'recommendations': {
                'total_made': FacultyReferralRecommendation.objects.filter(faculty=user).count(),
                'recent': recs_data,
            },
            'top_students_to_recommend': students_data,
            'monthly_earnings': monthly_earnings,
        })
