import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

def is_webhook_idempotent(event_id, prefix="webhook_idemp", timeout_hours=48):
    """
    Checks if a webhook event ID has already been processed.
    Returns True if safe to process (new event).
    Returns False if already processed (duplicate event).
    
    This uses Redis (if configured) via Django's cache framework to atomically
    set the key if it doesn't exist, preventing race conditions.
    """
    if not event_id:
        return True # Can't track if no ID
        
    cache_key = f"{prefix}:{event_id}"
    
    # cache.add only returns True if the key didn't already exist
    # This is an atomic operation in Redis
    is_new = cache.add(cache_key, "processed", timeout=timeout_hours * 3600)
    
    if not is_new:
        logger.info(f"Ignored duplicate webhook event: {event_id}")
        
    return is_new
