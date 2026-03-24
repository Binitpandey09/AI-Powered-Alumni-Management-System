from django.views.generic import TemplateView
from django.shortcuts import redirect
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


class ReferralBoardPageView(JWTLoginRequiredMixin, TemplateView):
    template_name = 'referrals/referral_board.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx['can_post'] = user.role in ('alumni', 'faculty')
        ctx['is_student'] = user.role == 'student'
        return ctx


class ReferralDetailPageView(JWTLoginRequiredMixin, TemplateView):
    template_name = 'referrals/referral_detail.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['referral_id'] = self.kwargs.get('referral_id')
        ctx['can_post'] = self.request.user.role in ('alumni', 'faculty')
        ctx['is_student'] = self.request.user.role == 'student'
        return ctx


class MyApplicationsPageView(JWTLoginRequiredMixin, TemplateView):
    template_name = 'referrals/my_applications.html'

    def dispatch(self, request, *args, **kwargs):
        token = request.COOKIES.get('access_token', '')
        user = get_user_from_token(token)
        if not user:
            return redirect(f'/auth/login/?next={request.path}')
        if user.role != 'student':
            return redirect('/referrals/')
        request.user = user
        return TemplateView.dispatch(self, request, *args, **kwargs)


class ManageApplicationsPageView(JWTLoginRequiredMixin, TemplateView):
    template_name = 'referrals/manage_applications.html'

    def dispatch(self, request, *args, **kwargs):
        token = request.COOKIES.get('access_token', '')
        user = get_user_from_token(token)
        if not user:
            return redirect(f'/auth/login/?next={request.path}')
        if user.role == 'student':
            return redirect('/referrals/')
        request.user = user
        return TemplateView.dispatch(self, request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['referral_id'] = self.kwargs.get('referral_id')
        return ctx


class SuccessStoriesPageView(JWTLoginRequiredMixin, TemplateView):
    template_name = 'referrals/success_stories.html'
