"""
Device Management Utilities
Handles device fingerprinting, registration, and trust management
"""
from django.utils import timezone
from DeviceManagement.models import UserDevice
from ua_parser import user_agent_parser
import hashlib
import logging

logger = logging.getLogger(__name__)


def get_device_fingerprint(request):
    """Generate unique device fingerprint from request"""
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    ip_address = get_client_ip(request)
    
    # Combine user agent and IP for fingerprint
    raw = f"{user_agent}|{ip_address}"
    return hashlib.sha256(raw.encode()).hexdigest()


def get_client_ip(request):
    """Extract client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def parse_user_agent(user_agent_string):
    """Parse user agent to extract device info"""
    parsed = user_agent_parser.Parse(user_agent_string)
    
    return {
        'browser': parsed['user_agent']['family'],
        'browser_version': parsed['user_agent']['major'],
        'os': parsed['os']['family'],
        'os_version': parsed['os']['major'],
        'device_type': determine_device_type(parsed)
    }


def determine_device_type(parsed_ua):
    """Determine device type from parsed UA"""
    device_family = parsed_ua.get('device', {}).get('family', '')
    
    if 'tablet' in device_family.lower():
        return 'tablet'
    elif 'mobile' in device_family.lower() or 'phone' in device_family.lower():
        return 'mobile'
    elif device_family and device_family != 'Other':
        return 'desktop'
    return 'unknown'


def register_device(user, request):
    """
    Register or update user device
    Returns UserDevice instance
    """
    user_agent_string = request.META.get('HTTP_USER_AGENT', '')
    ip_address = get_client_ip(request)
    device_fingerprint = get_device_fingerprint(request)
    
    # Parse user agent
    device_info = parse_user_agent(user_agent_string)
    
    # Get or create device
    device, created = UserDevice.objects.get_or_create(
        user=user,
        device_fingerprint=device_fingerprint,
        defaults={
            'user_agent': user_agent_string,
            'last_ip': ip_address,
            **device_info
        }
    )
    
    # Update last seen if device exists
    if not created:
        device.last_seen = timezone.now()
        device.last_ip = ip_address
        device.save()
    
    logger.info(f"Device {'registered' if created else 'updated'} for user {user.email}")
    
    return device


def is_trusted_device(user, request):
    """Check if current device is trusted"""
    device_fingerprint = get_device_fingerprint(request)
    
    try:
        device = UserDevice.objects.get(
            user=user,
            device_fingerprint=device_fingerprint,
            is_active=True
        )
        return device.trust_level == 'trusted'
    except UserDevice.DoesNotExist:
        return False


def revoke_device(user, device_id):
    """Revoke/deactivate a device"""
    try:
        device = UserDevice.objects.get(id=device_id, user=user)
        device.is_active = False
        device.revoked_at = timezone.now()
        device.save()
        
        logger.info(f"Device {device_id} revoked for user {user.email}")
        return True
    except UserDevice.DoesNotExist:
        logger.warning(f"Device {device_id} not found for user {user.email}")
        return False


def require_device_verification(user, request):
    """
    Check if device verification is required
    Returns True if device is new or untrusted
    """
    device_fingerprint = get_device_fingerprint(request)
    
    try:
        device = UserDevice.objects.get(
            user=user,
            device_fingerprint=device_fingerprint,
            is_active=True
        )
        # Require verification if not verified or untrusted
        return not device.is_verified or device.trust_level == 'untrusted'
    except UserDevice.DoesNotExist:
        # New device always requires verification
        return True


def get_user_devices(user):
    """Get all devices for a user"""
    devices = UserDevice.objects.filter(user=user, is_active=True).order_by('-last_seen')
    
    return [
        {
            'id': d.id,
            'browser': d.browser,
            'os': d.os,
            'device_type': d.device_type,
            'last_ip': d.last_ip,
            'last_seen': d.last_seen.isoformat() if d.last_seen else None,
            'is_current': False,  # Can be determined by comparing fingerprints
            'trust_level': d.trust_level,
            'created_at': d.created_at.isoformat() if d.created_at else None,
        }
        for d in devices
    ]

