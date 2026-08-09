"""
OTP Utilities for Authentication
Handles TOTP generation, QR codes, email/SMS sending, rate limiting, and OTP hashing
"""
import hashlib
import secrets
import pyotp
import qrcode
import io
import base64
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.core.cache import cache
from twilio.rest import Client
import logging

logger = logging.getLogger(__name__)

OTP_EXPIRY_MINUTES = 10
DAILY_OTP_LIMIT = 10


def generate_totp_secret():
    """Generate a new base32 secret for TOTP"""
    return pyotp.random_base32()


def generate_totp_otp(secret):
    """Generate a 6-digit OTP code from secret"""
    totp = pyotp.TOTP(secret, interval=60 * OTP_EXPIRY_MINUTES)
    return totp.now()


def verify_totp_otp(secret, otp):
    """
    Verify a TOTP code against the secret.
    Uses the standard 30-second interval so codes from authenticator apps
    (Google Authenticator, Authy, etc.) verify correctly.
    """
    totp = pyotp.TOTP(secret)
    return totp.verify(otp, valid_window=1)


def generate_qr_code(secret, email):
    """
    Generate QR code for 2FA setup
    Returns base64 encoded PNG image
    """
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name='Qomrade'
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"


def send_email_otp(email, otp, action='login'):
    """
    Send OTP via email with HTML template
    action: 'login', 'password_reset', '2fa_setup', 'registration'
    """
    action_text = {
        'login': 'Login Verification',
        'password_reset': 'Password Reset',
        '2fa_setup': '2FA Setup',
        'registration': 'Email Verification'
    }.get(action, 'Verification')
    
    subject = f'Qomrade - {action_text} Code'
    
    html_message = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .otp-code {{ font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #667eea; text-align: center; padding: 20px; background: white; border-radius: 8px; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Qomrade</h1>
                <p>{action_text}</p>
            </div>
            <div class="content">
                <p>Hello,</p>
                <p>Your verification code is:</p>
                <div class="otp-code">{otp}</div>
                <p>This code will expire in {OTP_EXPIRY_MINUTES} minutes.</p>
                <p>If you didn't request this code, please ignore this email.</p>
            </div>
            <div class="footer">
                <p>&copy; 2025 Qomrade. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        send_mail(
            subject,
            f'Your {action_text} code is: {otp}',
            settings.EMAIL_HOST_USER,
            [email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"OTP email sent to {email} for {action}")
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {str(e)}")
        return False


def send_sms_otp(phone_number, otp, action='login'):
    """Send OTP via Twilio SMS"""
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        message_body = f"Your Qomrade verification code is: {otp}. Valid for {OTP_EXPIRY_MINUTES} minutes."
        
        message = client.messages.create(
            body=message_body,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        
        logger.info(f"SMS OTP sent to {phone_number} for {action}. SID: {message.sid}")
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS OTP to {phone_number}: {str(e)}")
        return False


def send_2fa_qr_code(email, secret, qr_code_data):
    """Send 2FA QR code via email"""
    subject = 'Qomrade - 2FA Setup QR Code'
    
    html_message = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .qr-container {{ text-align: center; margin: 20px 0; }}
            img {{ max-width: 300px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>2FA Setup for Qomrade</h2>
            <p>Scan this QR code with your authenticator app:</p>
            <div class="qr-container">
                <img src="{qr_code_data}" alt="QR Code" />
            </div>
            <p>Or manually enter this secret key:</p>
            <p><strong>{secret}</strong></p>
        </div>
    </body>
    </html>
    """
    
    try:
        send_mail(
            subject,
            f'Your 2FA secret: {secret}',
            settings.EMAIL_HOST_USER,
            [email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send 2FA QR email: {str(e)}")
        return False


def check_otp_rate_limit(user_id, action):
    """
    Check if user can send OTP (max 10 per day)
    Returns (can_send: bool, remaining: int)
    """
    cache_key = f"otp_count_{user_id}_{action}"
    count = cache.get(cache_key, 0)
    
    can_send = count < DAILY_OTP_LIMIT
    remaining = max(0, DAILY_OTP_LIMIT - count)
    
    return can_send, remaining


def increment_otp_count(user_id, action):
    """Increment OTP counter for rate limiting"""
    cache_key = f"otp_count_{user_id}_{action}"
    count = cache.get(cache_key, 0)
    
    # Set expiry to 24 hours
    cache.set(cache_key, count + 1, 60 * 60 * 24)


# ============================================================================
# OTP HASHING UTILITIES
# ============================================================================

def hash_otp(value):
    """
    Hash an OTP value with a random salt using SHA-256.
    Returns 'salt$hash' format string suitable for DB storage.
    """
    salt = secrets.token_hex(8)
    hashed = hashlib.sha256((salt + str(value)).encode()).hexdigest()
    return f"{salt}${hashed}"


def verify_otp(value, stored):
    """
    Verify an OTP value against a 'salt$hash' stored string.
    Returns True if the value matches, False otherwise.
    """
    if not stored or '$' not in stored:
        return False
    try:
        salt, hashed = stored.split('$', 1)
        return hashlib.sha256((salt + str(value)).encode()).hexdigest() == hashed
    except (ValueError, AttributeError):
        return False


# ============================================================================
# OTP BRUTE-FORCE / ATTEMPT LOCKOUT
# ============================================================================

#: Maximum failed verification attempts before the OTP is invalidated.
MAX_OTP_ATTEMPTS = 5

#: Window (in seconds) during which failed attempts are counted.
OTP_ATTEMPT_WINDOW = 60 * 15  # 15 minutes


def get_otp_attempts(user_id, action):
    """Number of recent failed OTP verification attempts."""
    return cache.get(f"otp_failures_{user_id}_{action}", 0)


def record_otp_failure(user_id, action):
    """Increment the failed-attempt counter for an OTP action."""
    key = f"otp_failures_{user_id}_{action}"
    count = cache.get(key, 0) + 1
    cache.set(key, count, OTP_ATTEMPT_WINDOW)
    return count


def clear_otp_failures(user_id, action):
    """Reset the failed-attempt counter after a successful verification."""
    cache.delete(f"otp_failures_{user_id}_{action}")


def otp_attempts_exhausted(user_id, action):
    """True once MAX_OTP_ATTEMPTS failed attempts have been recorded."""
    return get_otp_attempts(user_id, action) >= MAX_OTP_ATTEMPTS


# ============================================================================
# TOTP BACKUP CODES
# ============================================================================

#: Number of backup codes generated on TOTP setup / regeneration.
BACKUP_CODE_COUNT = 10

#: Length of each generated backup code (e.g. "ABCD-EFGH").
BACKUP_CODE_LENGTH = 8


def generate_backup_codes(count=BACKUP_CODE_COUNT, length=BACKUP_CODE_LENGTH):
    """Generate a list of human-readable backup codes (returned as plaintext)."""
    codes = []
    while len(codes) < count:
        raw = secrets.token_urlsafe(9).replace('-', '').replace('_', '')[:length]
        code = f"{raw[:4]}-{raw[4:]}".upper()
        if code not in codes:
            codes.append(code)
    return codes


def hash_backup_codes(codes):
    """Hash backup codes for storage (comma-separated 'salt$hash' strings)."""
    return ','.join(hash_otp(c) for c in codes)


def verify_backup_code(stored, code):
    """
    Check a submitted code against the stored hashed backup codes.
    Returns True on match; the caller must persist the rotated list.
    """
    if not stored:
        return False
    hashes = [h for h in stored.split(',') if h]
    for h in hashes:
        if verify_otp(code, h):
            return True
    return False


def remove_backup_code(stored, code):
    """
    Return the stored list with the matched backup code removed.
    Returns None if the code did not match any stored hash.
    """
    if not stored:
        return None
    hashes = [h for h in stored.split(',') if h]
    remaining = [h for h in hashes if not verify_otp(code, h)]
    if len(remaining) == len(hashes):
        return None
    return ','.join(remaining)
