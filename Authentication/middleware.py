from django.utils import timezone
from django.core.cache import cache

class ActiveUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            now = timezone.now()
            # Only update last_seen (throttled to once per minute to reduce DB writes)
            cache_key = f'user_lastseen_{request.user.id}'
            if not cache.get(cache_key):
                request.user.last_seen = now
                request.user.save(update_fields=['last_seen'])
                cache.set(cache_key, True, 60)  # throttle for 60 seconds

        response = self.get_response(request)
        return response

