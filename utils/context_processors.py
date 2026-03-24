import time
from django.conf import settings


def user_context(request):
    """Expose authenticated user to all templates."""
    return {'auth_user': request.user}


def cache_bust(request):
    """In DEBUG mode, provide a timestamp so static files are never cached."""
    return {'CACHE_BUST': int(time.time()) if settings.DEBUG else '1'}
