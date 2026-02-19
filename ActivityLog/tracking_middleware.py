"""
Tracking middleware for automatic activity logging.
Logs all write API calls (POST/PUT/PATCH/DELETE) and connection security.
Respects user consent preferences and includes rate limiting.
"""
from ActivityLog.models import UserActivity, PermissionConsent
from ActivityLog.verification_utils import get_client_ip, log_connection_security
from django.utils import timezone
from django.core.cache import cache
import logging
import json
import re

logger = logging.getLogger(__name__)


# Human-readable descriptions for common API endpoints
ENDPOINT_DESCRIPTIONS = {
    # Authentication
    r'^/auth/login': ('login', 'Logged in'),
    r'^/auth/logout': ('logout', 'Logged out'),
    r'^/auth/register': ('register', 'Registered account'),
    r'^/auth/password': ('password_change', 'Password action'),
    r'^/auth/.*totp': ('security', '2FA action'),
    r'^/auth/.*otp': ('security', 'OTP verification'),
    
    # Payments
    r'^/api/payments/.*deposit': ('payment', 'Deposit'),
    r'^/api/payments/.*withdraw': ('payment', 'Withdrawal'),
    r'^/api/payments/.*transfer': ('payment', 'Transfer'),
    r'^/api/payments/.*payout': ('payment', 'Payout'),
    r'^/api/payments/groups': ('group_action', 'Payment group action'),
    r'^/api/payments': ('payment', 'Payment action'),
    
    # Social
    r'^/api/opinions/.*/like': ('interaction', 'Liked opinion'),
    r'^/api/opinions/.*/repost': ('interaction', 'Reposted opinion'),
    r'^/api/opinions/.*/comment': ('interaction', 'Commented on opinion'),
    r'^/api/opinions': ('interaction', 'Opinion action'),
    
    # Resources
    r'^/api/resources': ('interaction', 'Resource action'),
    
    # Events
    r'^/api/events/.*/rsvp': ('interaction', 'RSVP to event'),
    r'^/api/events': ('interaction', 'Event action'),
    
    # Rooms / Messages
    r'^/api/rooms/.*/messages': ('interaction', 'Room message'),
    r'^/api/rooms/.*/join': ('interaction', 'Joined room'),
    r'^/api/rooms/.*/leave': ('interaction', 'Left room'),
    r'^/api/rooms': ('interaction', 'Room action'),
    r'^/api/messages': ('interaction', 'Direct message'),
    
    # Content
    r'^/api/articles': ('interaction', 'Article action'),
    r'^/api/announcements': ('interaction', 'Announcement action'),
    r'^/api/tasks': ('interaction', 'Task action'),
    
    # Organizations / Institutions
    r'^/api/organizations': ('interaction', 'Organization action'),
    r'^/api/institutions': ('interaction', 'Institution action'),
    r'^/api/specializations': ('interaction', 'Specialization action'),
    
    # Funding / Careers
    r'^/api/funding': ('interaction', 'Funding action'),
    r'^/api/careers': ('interaction', 'Career action'),
    
    # AI
    r'^/api/qomai': ('interaction', 'AI assistant query'),
    
    # Research
    r'^/api/research': ('interaction', 'Research action'),
    
    # Notifications
    r'^/api/notifications': ('interaction', 'Notification action'),
    
    # Activity & Consent
    r'^/api/activity/consents': ('permission_change', 'Consent updated'),
    r'^/api/activity/export': ('download', 'Exported activity log'),
    
    # User management
    r'^/users': ('settings_change', 'Account action'),
    
    # Devices
    r'^/api/devices': ('device', 'Device management'),
}

# HTTP method → action verb mapping
METHOD_VERBS = {
    'POST': 'Created',
    'PUT': 'Updated',
    'PATCH': 'Updated',
    'DELETE': 'Deleted',
}


class ActivityTrackingMiddleware:
    """
    Django middleware that automatically logs:
    1. All write API calls (POST, PUT, PATCH, DELETE) for authenticated users
    2. Connection security information (once per session)
    
    Respects user consent for activity_logging permission.
    Rate-limited: max 1 log per user per endpoint per 2 seconds.
    """
    
    # Paths to skip tracking entirely
    SKIP_PATHS = (
        '/static/', '/media/', '/admin/', '/favicon.ico',
        '/health/', '/__debug__/',
    )
    
    # Paths to skip even for write operations (polling, heartbeats)
    SKIP_WRITE_PATHS = (
        'typing', 'heartbeat', 'status', 'read_receipt',
        'mark_read', 'online',
    )
    
    # Rate limit: only log connection security once per session
    CONNECTION_LOG_SESSION_KEY = '_connection_logged'
    
    # Rate limit window for API tracking (seconds)
    RATE_LIMIT_SECONDS = 2
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Pre-compile endpoint patterns
        self._compiled_patterns = [
            (re.compile(pattern), info)
            for pattern, info in ENDPOINT_DESCRIPTIONS.items()
        ]
    
    def __call__(self, request):
        # Process request
        response = self.get_response(request)
        
        # Only track authenticated users
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return response
        
        # Skip certain paths
        path = request.path
        if any(path.startswith(skip) for skip in self.SKIP_PATHS):
            return response
        
        user = request.user
        
        try:
            # 1. Log connection security (once per session)
            if hasattr(request, 'session'):
                if not request.session.get(self.CONNECTION_LOG_SESSION_KEY):
                    log_connection_security(user, request)
                    request.session[self.CONNECTION_LOG_SESSION_KEY] = True
            
            # 2. Log write API calls (POST, PUT, PATCH, DELETE)
            method = request.method
            if method in ('POST', 'PUT', 'PATCH', 'DELETE'):
                # Skip polling/noisy endpoints
                if any(skip in path for skip in self.SKIP_WRITE_PATHS):
                    return response
                
                # Skip activity log's own endpoints (prevent recursion)
                if '/api/activity/activities/' in path and method == 'POST':
                    return response
                
                self._log_api_request(user, request, response, method, path)
        
        except Exception as e:
            logger.warning(f"Activity tracking middleware error: {e}")
        
        return response
    
    def _log_api_request(self, user, request, response, method, path):
        """Log an API write operation as a UserActivity record."""
        
        # Check consent (respect user's activity_logging preference)
        try:
            consent = PermissionConsent.objects.get(
                user=user, permission_type='activity_logging'
            )
            if not consent.is_granted:
                return  # User has opted out
        except PermissionConsent.DoesNotExist:
            pass  # No consent record = default allow
        
        # Rate limit: prevent flooding from rapid repeated calls
        cache_key = f"activity_rate:{user.id}:{path}:{method}"
        if cache.get(cache_key):
            return  # Already logged recently
        cache.set(cache_key, True, self.RATE_LIMIT_SECONDS)
        
        # Determine activity type and description from endpoint
        activity_type, base_description = self._match_endpoint(path)
        verb = METHOD_VERBS.get(method, method)
        status_code = response.status_code
        
        # Build human-readable description
        if base_description:
            description = f"{base_description} ({verb})"
        else:
            # Fallback: derive from path
            path_parts = [p for p in path.strip('/').split('/') if p]
            resource = path_parts[-1] if path_parts else 'resource'
            # Clean up UUIDs and IDs from description
            if len(resource) > 20 or resource.replace('-', '').isalnum() and len(resource) > 8:
                resource = path_parts[-2] if len(path_parts) > 1 else 'resource'
            description = f"{verb} {resource}"
        
        # Add status context
        if status_code >= 400:
            description += f" (failed: {status_code})"
        
        # Build metadata
        metadata = {
            'method': method,
            'path': path,
            'status_code': status_code,
            'content_type': request.content_type or '',
        }
        
        # Safely extract minimal request info (no sensitive data)
        try:
            if hasattr(request, 'data') and isinstance(request.data, dict):
                # Only store keys, never values (security)
                metadata['request_fields'] = list(request.data.keys())[:20]
        except Exception:
            pass
        
        # Create the activity record
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        UserActivity.objects.create(
            user=user,
            activity_type=activity_type,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata,
            request_method=method,
            endpoint=path[:500],  # Truncate to field max
            status_code=status_code,
        )
    
    def _match_endpoint(self, path):
        """Match a request path to an activity type and description."""
        for pattern, (activity_type, description) in self._compiled_patterns:
            if pattern.search(path):
                return activity_type, description
        return 'api_request', ''
