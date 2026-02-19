"""
Verification utilities for activity tracking.
Handles connection security analysis, IP geolocation, and centralized activity logging.
"""
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Extract client IP from request, handling proxies"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def check_connection_security(request):
    """
    Analyze the security of the incoming connection.
    Returns a dict with security info.
    """
    ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    # Check HTTPS
    is_https = request.is_secure() or request.META.get('HTTP_X_FORWARDED_PROTO', '') == 'https'
    
    # Detect proxy/VPN from headers
    proxy_headers = [
        'HTTP_X_FORWARDED_FOR',
        'HTTP_X_REAL_IP',
        'HTTP_VIA',
        'HTTP_X_PROXY_ID',
    ]
    is_proxy = any(request.META.get(h) for h in proxy_headers)
    
    # VPN detection heuristic (basic - checking for known VPN-related headers)
    is_vpn = bool(request.META.get('HTTP_X_FORWARDED_FOR', '').count(',') > 1)
    
    # Security level determination
    if is_https and not is_proxy:
        security_level = 'secure'
    elif is_https and is_proxy:
        security_level = 'warning'
    elif not is_https:
        security_level = 'unsafe'
    else:
        security_level = 'unknown'
    
    return {
        'ip_address': ip,
        'is_https': is_https,
        'is_vpn': is_vpn,
        'is_proxy': is_proxy,
        'security_level': security_level,
        'user_agent': user_agent,
    }


def get_ip_geolocation(ip):
    """
    Get geolocation info for an IP address using free ip-api.com.
    Returns dict with country, city, isp, or empty dict on failure.
    """
    import requests as http_requests
    
    try:
        # Skip private/local IPs
        if ip in ('127.0.0.1', '::1', 'localhost') or ip.startswith(('10.', '172.', '192.168.')):
            return {'country': 'Local', 'city': 'Local', 'isp': 'Local Network'}
        
        response = http_requests.get(
            f'http://ip-api.com/json/{ip}?fields=status,country,city,isp,proxy',
            timeout=3
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return {
                    'country': data.get('country', ''),
                    'city': data.get('city', ''),
                    'isp': data.get('isp', ''),
                    'is_proxy': data.get('proxy', False),
                }
    except Exception as e:
        logger.warning(f"IP geolocation failed for {ip}: {e}")
    
    return {}


def log_user_activity(user, activity_type, description, request=None, metadata=None):
    """
    Centralized activity logger. Creates a UserActivity record.
    Respects user consent for activity_logging permission.
    """
    from ActivityLog.models import UserActivity, PermissionConsent
    
    # Check if user has consented to activity logging
    try:
        consent = PermissionConsent.objects.get(
            user=user, permission_type='activity_logging'
        )
        if not consent.is_granted:
            return None  # User has not consented
    except PermissionConsent.DoesNotExist:
        pass  # No consent record = default allow for basic logging
    
    ip_address = None
    user_agent = ''
    
    if request:
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    activity = UserActivity.objects.create(
        user=user,
        activity_type=activity_type,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {}
    )
    
    return activity


def log_connection_security(user, request):
    """
    Log connection security information for a user.
    Only logs if user has consented to internet_connection tracking.
    """
    from ActivityLog.models import ConnectionSecurityLog, PermissionConsent
    
    # Check consent
    try:
        consent = PermissionConsent.objects.get(
            user=user, permission_type='internet_connection'
        )
        if not consent.is_granted:
            return None
    except PermissionConsent.DoesNotExist:
        return None  # Require explicit consent for connection tracking
    
    security_info = check_connection_security(request)
    geo_info = get_ip_geolocation(security_info['ip_address'])
    
    log = ConnectionSecurityLog.objects.create(
        user=user,
        ip_address=security_info['ip_address'],
        is_https=security_info['is_https'],
        is_vpn=security_info['is_vpn'],
        is_proxy=security_info['is_proxy'] or geo_info.get('is_proxy', False),
        security_level=security_info['security_level'],
        country=geo_info.get('country', ''),
        city=geo_info.get('city', ''),
        isp=geo_info.get('isp', ''),
        user_agent=security_info['user_agent'],
    )
    
    return log


def log_search_activity(user, query, search_type='general', results_count=0, request=None, metadata=None):
    """
    Log a search query. Only logs if user has consented to search_history tracking.
    """
    from ActivityLog.models import SearchActivityLog, PermissionConsent
    
    # Check consent
    try:
        consent = PermissionConsent.objects.get(
            user=user, permission_type='search_history'
        )
        if not consent.is_granted:
            return None
    except PermissionConsent.DoesNotExist:
        return None  # Require explicit consent for search tracking
    
    ip_address = get_client_ip(request) if request else None
    
    log = SearchActivityLog.objects.create(
        user=user,
        query=query,
        search_type=search_type,
        results_count=results_count,
        ip_address=ip_address,
        metadata=metadata or {}
    )
    
    return log
