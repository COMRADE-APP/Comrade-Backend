from django.utils import timezone
from django.core.cache import cache

class ActiveUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            now = timezone.now()
            # Update last_seen
            request.user.last_seen = now
            request.user.is_online = True
            request.user.save(update_fields=['last_seen', 'is_online'])

            # Set a cache key for online status (expires in 5 mins)
            # This is useful for efficient "is_online" checks without hitting DB constantly
            # key = f'user_online_{request.user.id}'
            # cache.set(key, True, 300) 

        response = self.get_response(request)
        return response
