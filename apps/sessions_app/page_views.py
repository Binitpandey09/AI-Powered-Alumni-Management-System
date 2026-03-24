from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.conf import settings as django_settings
from utils.auth_helpers import get_user_from_token


class JWTLoginRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        token = request.COOKIES.get('access_token', '')
        user = get_user_from_token(token)
        if not user:
            return redirect(f'/auth/login/?next={request.path}')
        if not user.is_profile_complete and request.path not in ('/profile/setup/',):
            return redirect('/profile/setup/')
        request.user = user
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['user'] = self.request.user
        ctx['user_role'] = self.request.user.role
        return ctx


class SessionsMarketplacePageView(JWTLoginRequiredMixin, TemplateView):
    template_name = 'sessions_app/sessions_marketplace.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx['can_host'] = user.role in ('alumni', 'faculty')
        return ctx


class SessionDetailPageView(JWTLoginRequiredMixin, TemplateView):
    template_name = 'sessions_app/session_detail.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['session_id'] = self.kwargs.get('session_id')
        ctx['razorpay_key_id'] = django_settings.RAZORPAY_KEY_ID
        return ctx


class MyBookingsPageView(JWTLoginRequiredMixin, TemplateView):
    template_name = 'sessions_app/my_bookings.html'

    def dispatch(self, request, *args, **kwargs):
        token = request.COOKIES.get('access_token', '')
        user = get_user_from_token(token)
        if not user:
            return redirect(f'/auth/login/?next={request.path}')
        if user.role != 'student':
            return redirect('/sessions/hosting/')
        request.user = user
        return TemplateView.dispatch(self, request, *args, **kwargs)


class HostedSessionsPageView(JWTLoginRequiredMixin, TemplateView):
    template_name = 'sessions_app/hosted_sessions.html'

    def dispatch(self, request, *args, **kwargs):
        token = request.COOKIES.get('access_token', '')
        user = get_user_from_token(token)
        if not user:
            return redirect(f'/auth/login/?next={request.path}')
        if user.role == 'student':
            return redirect('/sessions/')
        request.user = user
        return TemplateView.dispatch(self, request, *args, **kwargs)


class EarningsPageView(JWTLoginRequiredMixin, TemplateView):
    template_name = 'sessions_app/earnings.html'

    def dispatch(self, request, *args, **kwargs):
        token = request.COOKIES.get('access_token', '')
        user = get_user_from_token(token)
        if not user:
            return redirect(f'/auth/login/?next={request.path}')
        if user.role not in ('alumni', 'faculty'):
            return redirect('/sessions/')
        request.user = user
        return TemplateView.dispatch(self, request, *args, **kwargs)
