import logging
from django.conf import settings
from DeviceManagement.models import UserDevice

logger = logging.getLogger(__name__)

# Firebase Cloud Messaging initialization
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    
    # Initialize Firebase app if not already initialized and credentials exist
    if not firebase_admin._apps and hasattr(settings, 'FIREBASE_CREDENTIALS_PATH'):
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)
        FIREBASE_ENABLED = True
    else:
        FIREBASE_ENABLED = bool(firebase_admin._apps)
except ImportError:
    FIREBASE_ENABLED = False
    logger.warning("firebase-admin not installed. Push notifications disabled.")


class PushNotificationService:
    """
    Service for sending push notifications via Firebase Cloud Messaging (FCM).
    """
    
    @staticmethod
    def send_to_user(user, title, body, data=None):
        """
        Send a push notification to all active devices for a user.
        """
        if not FIREBASE_ENABLED:
            logger.info(f"FCM disabled. Would have sent: {title} to user {user.id}")
            return False
            
        if not user.is_active:
            return False
            
        # Get active FCM tokens for the user
        devices = UserDevice.objects.filter(
            user=user, 
            is_active=True,
            fcm_token__isnull=False
        ).exclude(fcm_token="")
        
        tokens = [device.fcm_token for device in devices]
        
        if not tokens:
            return False
            
        return PushNotificationService._send_multicast(tokens, title, body, data)
        
    @staticmethod
    def _send_multicast(tokens, title, body, data=None):
        """
        Send multicast message to multiple FCM tokens.
        """
        try:
            # Construct message
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                tokens=tokens,
            )
            
            # Send message
            response = messaging.send_multicast(message)
            
            # Log results
            if response.failure_count > 0:
                logger.warning(
                    f"FCM Multicast sent with failures. "
                    f"Success: {response.success_count}, Failed: {response.failure_count}"
                )
                
            return response.success_count > 0
            
        except Exception as e:
            logger.error(f"Error sending FCM multicast: {e}")
            return False
