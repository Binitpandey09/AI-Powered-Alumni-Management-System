from django.shortcuts import redirect
from django.views.generic import TemplateView
from utils.auth_helpers import get_user_from_token


class JWTLoginRequiredMixin:
    """
    Mixin that validates the httponly 'access_token' cookie before
    serving a dashboard page. Falls back to /auth/login/ if missing/invalid.
    """

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


class AlumniDashboardView(JWTLoginRequiredMixin, TemplateView):
    template_name = 'dashboard/alumni_dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        # Redirect non-alumni to their own dashboard
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
