"""
Activity Logging Utilities
Track user authentication activities for security monitoring
"""
from ActivityLog.models import UserActivity, ActionLog
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Extract client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_user_activity(user, activity_type, request, description=''):
    """Log high-level user activity"""
    try:
        UserActivity.objects.create(
            user=user,
            activity_type=activity_type,
            description=description,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        logger.debug(f"Activity logged: {activity_type} for {user.email if user else 'anonymous'}")
    except Exception as e:
        logger.error(f"Failed to log activity: {str(e)}")


def log_action(user, action, details, request):
    """Log detailed action with JSON details"""
    try:
        ActionLog.objects.create(
            user=user,
            action=action,
            details=details,
            ip_address=get_client_ip(request)
        )
    except Exception as e:
        logger.error(f"Failed to log action: {str(e)}")


def log_login_attempt(user, request, success, method='password'):
    """Log login attempt"""
    activity_type = 'login' if success else 'login'
    description = f"{'Successful' if success else 'Failed'} login via {method}"
    
    if user:
        log_user_activity(user, activity_type, request, description)
        log_action(user, 'login_attempt', {
            'success': success,
            'method': method,
            'ip': get_client_ip(request)
        }, request)


def log_password_reset(user, request, stage='request'):
    """Log password reset activity"""
    log_user_activity(user, 'password_change', request, f'Password reset {stage}')
    log_action(user, 'password_reset', {
        'stage': stage
    }, request)


def log_2fa_activity(user, request, action):
    """Log 2FA related activities"""
    log_user_activity(user, 'security', request, f'2FA {action}')
    log_action(user, '2fa_activity', {
        'action': action
    }, request)


def log_device_activity(user, request, action, device_id=None):
    """Log device management activities"""
    log_user_activity(user, 'device', request, f'Device {action}')
    log_action(user, 'device_management', {
        'action': action,
        'device_id': device_id
    }, request)
