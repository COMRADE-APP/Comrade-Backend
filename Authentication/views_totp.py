"""
TOTP (Two-Factor Authentication) Views
Implements TOTP setup, verification, and management
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
import pyotp
import qrcode
import io
import base64
from django.core.cache import cache
from Authentication.models import CustomUser
from Authentication.otp_utils import (
    record_otp_failure,
    clear_otp_failures,
    otp_attempts_exhausted,
)
from comrade.throttles import OTPThrottle


class TOTPSetupView(APIView):
    """Generate QR code for TOTP setup"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        # Generate TOTP secret
        secret = pyotp.random_base32()
        
        # Store secret temporarily in cache (10 minutes)
        cache.set(f'totp_setup_{user.id}', secret, 600)
        
        # Generate TOTP URI
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name='Qomrade Platform'
        )
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return Response({
            'secret': secret,
            'qr_code': f'data:image/png;base64,{qr_code_base64}',
            'provisioning_uri': provisioning_uri
        })


class TOTPVerifySetupView(APIView):
    """Verify TOTP code  during setup and save to user profile"""
    permission_classes = [IsAuthenticated]
    throttle_classes = [OTPThrottle]
    
    def post(self, request):
        user = request.user
        code = request.data.get('code')
        
        if not code:
            return Response(
                {'error': 'TOTP code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if otp_attempts_exhausted(user.id, 'totp_setup'):
            return Response(
                {'error': 'Too many invalid attempts. Try again later.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        # Get temporary secret from cache
        secret = cache.get(f'totp_setup_{user.id}')
        if not secret:
            return Response(
                {'error': 'Setup session expired. Please start over.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify code
        totp = pyotp.TOTP(secret)
        if not totp.verify(code, valid_window=1):
            record_otp_failure(user.id, 'totp_setup')
            return Response(
                {'error': 'Invalid TOTP code'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        clear_otp_failures(user.id, 'totp_setup')
        
        # Save to user profile (assuming CustomUser has totp_secret field)
        # TODO: Add totp_secret and totp_enabled fields to CustomUser model
        # user.totp_secret = secret
        # user.totp_enabled = True
        # user.save()
        
        # Clear cache
        cache.delete(f'totp_setup_{user.id}')
        
        # Generate backup codes
        backup_codes = [pyotp.random_base32() [:8] for _ in range(10)]
        # TODO: Store backup codes securely (hashed)
        
        return Response({
            'message': 'TOTP enabled successfully',
            'backup_codes': backup_codes
        })


class TOTPVerifyLoginView(APIView):
    """Verify TOTP code during login"""
    permission_classes = [IsAuthenticated]
    throttle_classes = [OTPThrottle]
    
    def post(self, request):
        user = request.user
        code = request.data.get('code')
        
        if not code:
            return Response(
                {'error': 'TOTP code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if otp_attempts_exhausted(user.id, 'totp_login'):
            return Response(
                {'error': 'Too many invalid attempts. Try again later.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        # TODO: Get secret from user profile
        # secret = user.totp_secret
        # if not secret or not user.totp_enabled:
        #     return Response(
        #         {'error': 'TOTP not enabled for this account'},
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        
        # Placeholder secret for now
        secret = cache.get(f'totp_secret_{user.id}')
        if not secret:
            return Response(
                {'error': 'TOTP not configured'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify code
        totp = pyotp.TOTP(secret)
        is_valid = totp.verify(code, valid_window=1)
        
        # TODO: Also check backup codes
        
        if not is_valid:
            record_otp_failure(user.id, 'totp_login')
            return Response(
                {'error': 'Invalid TOTP code'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        clear_otp_failures(user.id, 'totp_login')
        
        return Response({
            'message': 'TOTP verified successfully',
            'verified': True
        })


class TOTPDisableView(APIView):
    """Disable TOTP for user account"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        password = request.data.get('password')
        
        if not password:
            return Response(
                {'error': 'Password required to disable TOTP'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify password
        if not user.check_password(password):
            return Response(
                {'error': 'Invalid password'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # TODO: Disable TOTP
        # user.totp_enabled = False
        # user.totp_secret = ''
        # user.save()
        
        # Clear cache
        cache.delete(f'totp_secret_{user.id}')
        
        return Response({
            'message': 'TOTP disabled successfully'
        })


class TOTPBackupCodesView(APIView):
    """Regenerate backup codes"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        password = request.data.get('password')
        
        if not password:
            return Response(
                {'error': 'Password required to regenerate backup codes'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify password
        if not user.check_password(password):
            return Response(
                {'error': 'Invalid password'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # TODO: Check if TOTP is enabled
        # if not user.totp_enabled:
        #     return Response(
        #         {'error': 'TOTP not enabled'},
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        
        # Generate new backup codes
        backup_codes = [pyotp.random_base32()[:8] for _ in range(10)]
        
        # TODO: Store backup codes securely (hashed)
        # Invalidate old backup codes
        
        return Response({
            'message': 'Backup codes regenerated successfully',
            'backup_codes': backup_codes
        })
