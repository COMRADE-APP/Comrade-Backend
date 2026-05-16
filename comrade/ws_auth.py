"""
WebSocket JWT Authentication Middleware for Django Channels.
Extracts the JWT token from the query string (?token=xxx) and
authenticates the user before the consumer connects.
"""
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from Authentication.models import CustomUser


@database_sync_to_async
def get_user_from_token(token_str):
    """Validate JWT and return the associated user or AnonymousUser."""
    try:
        access_token = AccessToken(token_str)
        user_id = access_token["user_id"]
        return CustomUser.objects.get(id=user_id)
    except (TokenError, CustomUser.DoesNotExist, KeyError):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom middleware that authenticates WebSocket connections
    using a JWT token passed in the query string.
    
    Usage in frontend:
        new WebSocket(`ws://host/ws/chat/${roomId}/?token=${accessToken}`)
    """
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)
        token_list = params.get("token", [])

        if token_list:
            scope["user"] = await get_user_from_token(token_list[0])
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)
