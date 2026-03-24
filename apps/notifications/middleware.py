"""
JWT WebSocket middleware — authenticates WS connections via:
  1. ?token=<access_token> query param
  2. access_token cookie
"""
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def get_user_from_token(token_key):
    """Validate a JWT access token and return the corresponding User or AnonymousUser."""
    try:
        from rest_framework_simplejwt.tokens import AccessToken
        from django.contrib.auth import get_user_model
        User = get_user_model()
        token = AccessToken(token_key)
        user_id = token['user_id']
        return User.objects.get(pk=user_id)
    except Exception:
        return AnonymousUser()


class JWTWebSocketMiddleware:
    """
    ASGI middleware that reads a JWT from the WS query string or cookie
    and populates scope['user'].
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'websocket':
            token = self._extract_token(scope)
            scope['user'] = await get_user_from_token(token) if token else AnonymousUser()
        return await self.app(scope, receive, send)

    @staticmethod
    def _extract_token(scope):
        # 1. Query param: ?token=...
        query_string = scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        if 'token' in params:
            return params['token'][0]

        # 2. Cookie: access_token=...
        headers = dict(scope.get('headers', []))
        cookie_header = headers.get(b'cookie', b'').decode()
        for part in cookie_header.split(';'):
            part = part.strip()
            if part.startswith('access_token='):
                return part[len('access_token='):]

        return None
