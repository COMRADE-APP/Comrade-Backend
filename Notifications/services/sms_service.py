import os
import logging
import africastalking

logger = logging.getLogger(__name__)

# Initialize Africa's Talking
# Requires environment variables: AT_USERNAME, AT_API_KEY
AT_USERNAME = os.getenv('AT_USERNAME', 'sandbox')
AT_API_KEY = os.getenv('AT_API_KEY', 'dummy_key')

try:
    africastalking.initialize(AT_USERNAME, AT_API_KEY)
    at_sms = africastalking.SMS
except Exception as e:
    logger.error(f"Failed to initialize Africa's Talking: {str(e)}")
    at_sms = None


def send_sms(phone_number: str, message: str) -> bool:
    """
    Sends an SMS using Africa's Talking.
    """
    if not phone_number or not message:
        logger.error("Phone number and message are required to send SMS.")
        return False
        
    # Format phone number ensuring it starts with '+'
    if not phone_number.startswith('+'):
        phone_number = f"+{phone_number}"
    
    if not at_sms:
        logger.error("Africa's Talking SMS service is not initialized.")
        return False
        
    try:
        # Africa's Talking expects a list of phone numbers
        response = at_sms.send(message, [phone_number])
        logger.info(f"Africa's Talking SMS sent to {phone_number}: {response}")
        return True
    except Exception as e:
        logger.error(f"Africa's Talking send failed for {phone_number}: {str(e)}")
        return False
