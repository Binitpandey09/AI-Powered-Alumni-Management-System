from django.views.generic import TemplateView
from django.shortcuts import redirect
from utils.auth_helpers import get_user_from_token
from django.conf import settings as django_settings


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


class WalletPageView(JWTLoginRequiredMixin, TemplateView):
    template_name = 'payments/wallet.html'

    def dispatch(self, request, *args, **kwargs):
        token = request.COOKIES.get('access_token', '')
        user = get_user_from_token(token)
        if not user:
            return redirect(f'/auth/login/?next={request.path}')
        if user.role not in ('alumni', 'faculty'):
            return redirect('/dashboard/student/')
        request.user = user
        return TemplateView.dispatch(self, request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['razorpay_key_id'] = django_settings.RAZORPAY_KEY_ID
        return ctx


class InvoicePageView(JWTLoginRequiredMixin, TemplateView):
    template_name = 'payments/invoice.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['invoice_number'] = self.kwargs.get('invoice_number', '')
        return ctx


class AdminPaymentsPageView(JWTLoginRequiredMixin, TemplateView):
    template_name = 'payments/admin_payments.html'

    def dispatch(self, request, *args, **kwargs):
        token = request.COOKIES.get('access_token', '')
        user = get_user_from_token(token)
        if not user:
            return redirect(f'/auth/login/?next={request.path}')
        if user.role != 'admin':
            return redirect('/dashboard/alumni/')
        request.user = user
        return TemplateView.dispatch(self, request, *args, **kwargs)
