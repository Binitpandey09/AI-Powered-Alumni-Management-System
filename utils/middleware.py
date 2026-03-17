from django.shortcuts import redirect
from .auth_helpers import get_user_from_token

# Page URL prefixes that require authentication
PROTECTED_PREFIXES = (
    '/dashboard/',
    '/feed/',
    '/sessions/',
    '/referrals/',
    '/profile/',
)

# Prefixes that are always public — never redirect
PUBLIC_PREFIXES = (
    '/',        # home
    '/auth/',   # all auth pages
    '/api/',    # DRF endpoints handle their own auth
    '/admin/',  # Django admin handles its own auth
    '/static/',
    '/media/',
    '/__debug__/',
)


class JWTAuthMiddleware:
    """
    Lightweight page-level auth guard.

    Reads the httponly 'access_token' cookie set by LoginVerifyOTPView.
    If a protected page is requested without a valid token, redirects to /auth/login/.
    API routes are untouched — DRF handles those independently.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info

        if self._is_protected(path):
            token = request.COOKIES.get('access_token', '')
            user = get_user_from_token(token)
            if user is None:
                return redirect(f'/auth/login/?next={path}')
            # Attach user so templates can access request.user
            request.user = user

        return self.get_response(request)

    @staticmethod
    def _is_protected(path: str) -> bool:
        # Explicitly public — skip guard
        for prefix in PUBLIC_PREFIXES:
            if path == prefix or (prefix != '/' and path.startswith(prefix)):
                return False
        # Check if it falls under a protected prefix
        for prefix in PROTECTED_PREFIXES:
            if path.startswith(prefix):
                return True
        return False
