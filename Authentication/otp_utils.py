"""
OTP Utilities for Authentication
Handles TOTP generation, QR codes, email sending, and rate limiting
"""
import pyotp
import qrcode
import io
import base64
import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

OTP_EXPIRY_MINUTES = 2
DAILY_OTP_LIMIT = 10


def generate_totp_secret():
    """Generate a new base32 secret for TOTP"""
    return pyotp.random_base32()


def generate_totp_otp(secret):
    """Generate a 6-digit OTP code from secret"""
    totp = pyotp.TOTP(secret, interval=60 * OTP_EXPIRY_MINUTES)
    return totp.now()


def verify_totp_otp(secret, otp):
    """Verify an OTP code against the secret"""
    totp = pyotp.TOTP(secret, interval=60 * OTP_EXPIRY_MINUTES)
    return totp.verify(otp, valid_window=1)


def generate_qr_code(secret, email):
    """
    Generate QR code for 2FA setup
    Returns base64 encoded PNG image
    """
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name='Comrade'
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
    
    subject = f'Comrade - {action_text} Code'
    
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
                <h1>Comrade</h1>
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
                <p>&copy; 2025 Comrade. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        send_mail(
            subject,
            f'Your {action_text} code is: {otp}',
            settings.DEFAULT_FROM_EMAIL,
            [email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"OTP email sent to {email} for {action}")
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {str(e)}")
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
