from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

User = get_user_model()


def get_user_from_token(token: str):
    """
    Decode a JWT access token string and return the corresponding User,
    or None if the token is missing, invalid, or the user doesn't exist.
    """
    if not token:
        return None
    try:
        validated = AccessToken(token)
        user_id = validated['user_id']
        return User.objects.get(id=user_id, is_active=True)
    except (TokenError, InvalidToken, User.DoesNotExist, KeyError):
        return None


def get_dashboard_url(user) -> str:
    """Return the role-appropriate dashboard URL for a user."""
    mapping = {
        'alumni':  '/dashboard/alumni/',
        'student': '/dashboard/student/',
        'faculty': '/dashboard/faculty/',
        'admin':   '/admin/',
    }
    return mapping.get(user.role, '/dashboard/student/')


def is_profile_complete(user) -> bool:
    """Return True if the user has completed their profile."""
    return bool(user.is_profile_complete)
