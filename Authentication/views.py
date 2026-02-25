"""
Authentication Views
Complete authentication system with OTP verification, 2FA, SMS fallback, password reset, and device management
"""
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import logging
import secrets

from Authentication.models import (
    CustomUser, Lecturer, OrgStaff, StudentAdmin, OrgAdmin, 
    InstAdmin, InstStaff, Profile, UserProfile
)
from Authentication.serializers import (
    LoginSerializer, CustomUserSerializer, LecturerSerializer, OrgStaffSerializer, 
    StudentAdminSerializer, OrgAdminSerializer, InstAdminSerializer, 
    InstStaffSerializer, ProfileSerializer, BaseUserSerializer
)
from Authentication.otp_utils import (
    generate_totp_secret, generate_totp_otp, verify_totp_otp, 
    generate_qr_code, send_email_otp, send_sms_otp, send_2fa_qr_code,
    check_otp_rate_limit, increment_otp_count, OTP_EXPIRY_MINUTES
)
from Authentication.device_utils import register_device, revoke_device, is_trusted_device
from Authentication.activity_logger import (
    log_user_activity, log_login_attempt, log_password_reset, 
    log_2fa_activity, log_device_activity
)

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # Disable authentication (prevents SessionAuth CSRF check)
    
    def post(self, request):
        print('-------------------', request.data, '-------------------')
        serializer = BaseUserSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Infer currency and language from email TLD / browser locale
            browser_locale = request.data.get('browser_locale', '')
            self._infer_preferences(user, browser_locale)
            
            # Log registration
            log_user_activity(user, 'register', request, "User registered")
            
            # Generate OTP for registration verification
            otp_code = str(secrets.SystemRandom().randint(100000, 999999))
            user.registration_otp = otp_code
            user.registration_otp_expires = timezone.now() + timezone.timedelta(minutes=OTP_EXPIRY_MINUTES)
            user.save()
            
            print(f'Registration OTP: {otp_code}')
            
            # Send OTP via email
            try:
                email_sent = send_email_otp(user.email, otp_code, action='registration')
                if not email_sent:
                    logger.error(f"Failed to send registration OTP to {user.email}")
            except Exception as e:
                logger.error(f"Failed to send registration OTP: {e}")
            
            return Response({
                "message": "Registration successful. Please verify your email with the OTP sent.",
                "email": user.email,
                "next_step": "verify_registration_otp"
            }, status=status.HTTP_201_CREATED)

        print('-------------------', serializer.errors, '-------------------')
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _infer_preferences(self, user, browser_locale):
        """Infer and set currency/language from email TLD and browser locale."""
        from Authentication.currency_utils import (
            infer_currency_from_email, infer_currency_from_locale,
            infer_language_from_email, infer_language_from_locale,
        )
        changed = False
        
        # Currency: email TLD first, then browser locale, then keep default (USD)
        if user.preferred_currency == 'USD':  # Only if not explicitly set
            currency = infer_currency_from_email(user.email)
            if not currency:
                currency = infer_currency_from_locale(browser_locale)
            if currency:
                user.preferred_currency = currency
                changed = True
        
        # Language: browser locale first, then email TLD, then keep default (en)
        if user.preferred_language == 'en':  # Only if not explicitly set
            language = infer_language_from_locale(browser_locale)
            if language == 'en':
                # Try email TLD as fallback
                email_lang = infer_language_from_email(user.email)
                if email_lang:
                    language = email_lang
            if language and language != 'en':
                user.preferred_language = language
                changed = True
        
        if changed:
            user.save(update_fields=['preferred_currency', 'preferred_language'])



@method_decorator(csrf_exempt, name='dispatch')
class RegisterVerifyView(APIView):
    """Verify registration OTP and activate user account"""
    permission_classes = [AllowAny]
    authentication_classes = []  # Disable authentication (prevents SessionAuth CSRF check)
    
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')
        
        if not email or not otp:
            return Response({"detail": "Email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if already verified
        if user.is_active:
            return Response({"detail": "Account already verified."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check OTP
        if not user.registration_otp or not user.registration_otp_expires:
            return Response({"detail": "No pending verification found."}, status=status.HTTP_400_BAD_REQUEST)
        
        if timezone.now() > user.registration_otp_expires:
            return Response({"detail": "Verification code expired."}, status=status.HTTP_400_BAD_REQUEST)
        
        if otp != user.registration_otp:
            return Response({"detail": "Invalid verification code."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Activate user and clear OTP
        user.is_active = True
        user.registration_otp = None
        user.registration_otp_expires = None
        
        # Set user type boolean flags
        flag_map = {
            'student': 'is_student',
            'lecturer': 'is_lecturer',
            'org_staff': 'is_org_staff',
            'org_admin': 'is_org_admin',
            'inst_admin': 'is_inst_admin',
            'inst_staff': 'is_inst_staff',
        }
        
        flag = flag_map.get(user.user_type)
        if flag:
            setattr(user, flag, True)
        
        user.save()
        
        # Create Profile automatically
        Profile.objects.get_or_create(user=user)
        
        # Create UserProfile for extended profile data
        from Authentication.models import UserProfile
        UserProfile.objects.get_or_create(user=user)
        
        log_user_activity(user, 'email_verified', request, "Email verified via OTP")
        
        # Generate JWT tokens so user is auto-logged in
        refresh = RefreshToken.for_user(user)
        
        return Response({
            "message": "Email verified successfully!",
            "email": user.email,
            "user_id": user.id,
            "first_name": user.first_name,
            "user_type": user.user_type,
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "next_step": "profile_setup"
        })


class VerifyView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        uid = request.GET.get('uid')
        token = request.GET.get('token')
        
        try:
            uid = force_str(urlsafe_base64_decode(uid))
            user = CustomUser.objects.get(pk=uid)
        except Exception:
            return Response({'detail': 'Invalid verification link.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if default_token_generator.check_token(user, token):
            user.is_active = True
            
            # Set user type boolean flags
            flag_map = {
                'student': 'is_student',
                'lecturer': 'is_lecturer',
                'org_staff': 'is_org_staff',
                'org_admin': 'is_org_admin',
                'inst_admin': 'is_inst_admin',
                'inst_staff': 'is_inst_staff',
            }
            
            flag = flag_map.get(user.user_type)
            if flag:
                setattr(user, flag, True)
            
            user.save()
            
            return Response({'detail': 'Email verified successfully. You can now login.'})
        return Response({'detail': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)


class MeView(APIView):
    """Get current authenticated user details"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)


class HeartbeatView(APIView):
    """
    Simple endpoint to keep user status 'online'.
    The ActiveUserMiddleware handles the actual status update.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response({"status": "alive"}, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # Disable authentication (prevents SessionAuth CSRF check)
    
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        otp_method = request.data.get('otp_method', 'email')  # 'email' or 'sms'
        
        user = authenticate(email=email, password=password)
        print('------------------------', request.data, '---------------------------')
        
        if user is None:
            log_login_attempt(None, request, False, "Invalid credentials")
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.is_active:
            return Response({
                "detail": "Account is not active. Please verify your email."
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Check if user has phone number for SMS option
        has_phone = bool(user.phone_number and user.phone_number != '0123456789')
        
        # If user chose SMS but doesn't have phone, default to email
        if otp_method == 'sms' and not has_phone:
            return Response({
                "detail": "No phone number registered. Please add a phone number or choose email verification.",
                "has_phone": False
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate OTP secret
        otp_secret = generate_totp_secret()
        otp_code = generate_totp_otp(otp_secret)
        
        if otp_method == 'sms' and has_phone:
            # Send via SMS
            can_send, remaining = check_otp_rate_limit(user.id, 'sms_login')
            if not can_send:
                return Response({
                    "detail": "Daily SMS limit reached. Please try email instead."
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            user.sms_otp = otp_code
            user.sms_otp_expires = timezone.now() + timezone.timedelta(minutes=OTP_EXPIRY_MINUTES)
            user.save()

            print(user.login_otp, '--------------------------')
            
            sms_sent = send_sms_otp(user.phone_number, otp_code, action='login')
            increment_otp_count(user.id, 'sms_login')
            
            if not sms_sent:
                return Response({
                    "detail": "Failed to send SMS code. Please try email instead."
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({
                "message": "Verification code sent to your phone.",
                "email": user.email,
                "phone_last_4": user.phone_number[-4:],
                "verification_required": True,
                "next_step": "verify_sms_otp",
                "otp_method": "sms"
            }, status=status.HTTP_200_OK)
        
        else:
            # Send via Email (default)
            can_send, remaining = check_otp_rate_limit(user.id, 'login')
            if not can_send:
                return Response({
                    "detail": "Daily OTP limit reached. Please try again tomorrow."
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            # Use static numeric OTP for email too (better UX than TOTP)
            otp_code = str(secrets.SystemRandom().randint(100000, 999999))
            
            user.login_otp = otp_code
            user.login_otp_expires = timezone.now() + timezone.timedelta(minutes=OTP_EXPIRY_MINUTES)
            user.save()

            print(user.login_otp, '--------------------------')
            
            email_sent = send_email_otp(user.email, otp_code, action='login')
            increment_otp_count(user.id, 'login')
            
            if not email_sent:
                return Response({
                    "detail": "Failed to send verification code."
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({
                "message": "Verification code sent to your email.",
                "email": user.email,
                "verification_required": True,
                "next_step": "verify_email_otp",
                "otp_method": "email",
                "has_phone": has_phone
            }, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class LoginVerifyView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # Disable authentication (prevents SessionAuth CSRF check)
    
    def post(self, request):
        print(request.data, '--------------------------')
        email = request.data.get('email')
        otp = request.data.get('otp')
        
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        
        # Verify Email OTP (this endpoint is for email OTP only)
        if not user.login_otp or not user.login_otp_expires:
            return Response({"detail": "No pending verification found."}, status=status.HTTP_400_BAD_REQUEST)
        
        if timezone.now() > user.login_otp_expires:
            return Response({"detail": "Verification code expired."}, status=status.HTTP_400_BAD_REQUEST)
        
        if otp != user.login_otp:
            print("Invalid verification code.")
            return Response({"detail": "Invalid verification code."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Clear OTP after successful verification
        user.login_otp = None
        user.login_otp_expires = None
        user.save()
        
        # Check if 2FA is enabled
        if user.totp_enabled:
            return Response({
                "message": "2FA verification required.",
                "verification_required": True,
                "next_step": "verify_2fa_totp",
                "email": user.email
            })
        
        # Complete login (no 2FA required)
        return self._complete_login(user, request)
    
    def _complete_login(self, user, request):
        """Complete login process with token generation"""
        register_device(user, request)
        log_login_attempt(user, request, True, method='email_otp')
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            "user_id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "user_type": user.user_type,
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "next_step": "complete"
        })


@method_decorator(csrf_exempt, name='dispatch')
class ResendOTPView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # Disable authentication (prevents SessionAuth CSRF check)
    
    def post(self, request):
        email = request.data.get('email')
        action_type = request.data.get('action_type', 'login')  # 'login' or 'registration'
        otp_method = request.data.get('otp_method', 'email')
        
        if not email:
            return Response({'detail': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
             return Response({'message': 'Code sent if account exists.'}, status=status.HTTP_200_OK)
             
        if not user.is_active:
             return Response({'detail': 'Account inactive.'}, status=status.HTTP_400_BAD_REQUEST)

        # Generate OTP
        otp_code = str(secrets.SystemRandom().randint(100000, 999999))
        
        if otp_method == 'sms':
            if not user.phone_number:
                return Response({'detail': 'No phone number.'}, status=status.HTTP_400_BAD_REQUEST)
                
            can_send, _ = check_otp_rate_limit(user.id, 'sms_login')
            if not can_send:
                return Response({'detail': 'Limit reached.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
                
            user.sms_otp = otp_code
            user.sms_otp_expires = timezone.now() + timezone.timedelta(minutes=OTP_EXPIRY_MINUTES)
            user.save()
            
            if send_sms_otp(user.phone_number, otp_code, action='login'):
                increment_otp_count(user.id, 'sms_login')
                return Response({'message': 'SMS sent.'}, status=status.HTTP_200_OK)
                
        else:
            can_send, _ = check_otp_rate_limit(user.id, 'login')
            if not can_send:
                return Response({'detail': 'Limit reached.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
                
            user.login_otp = otp_code
            user.login_otp_expires = timezone.now() + timezone.timedelta(minutes=OTP_EXPIRY_MINUTES)
            user.save()
            
            if send_email_otp(user.email, otp_code, action='login'):
                increment_otp_count(user.id, 'login')
                return Response({'message': 'Email sent.'}, status=status.HTTP_200_OK)
                
        return Response({'detail': 'Failed to send.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class Verify2FAView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')
        
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        
        if not user.totp_enabled:
            return Response({"detail": "2FA not enabled for this user."}, status=status.HTTP_400_BAD_REQUEST)
        
        if verify_totp_otp(user.totp_secret, otp):
            log_2fa_activity(user, request, 'verify')
            register_device(user, request)
            
            refresh = RefreshToken.for_user(user)
            return Response({
                "user_id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "user_type": user.user_type,
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "next_step": "complete"
            })
        
        return Response({"detail": "Invalid 2FA code."}, status=status.HTTP_400_BAD_REQUEST)


class VerifySMSOTPView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')
        
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        
        if not user.sms_otp or not user.sms_otp_expires:
            return Response({"detail": "No pending SMS verification."}, status=status.HTTP_400_BAD_REQUEST)
        
        if timezone.now() > user.sms_otp_expires:
            return Response({"detail": "SMS code expired."}, status=status.HTTP_400_BAD_REQUEST)
        
        if user.sms_otp != otp:
            return Response({"detail": "Invalid SMS code."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Clear OTP
        user.sms_otp = None
        user.sms_otp_expires = None
        user.save()
        
        # Complete login
        register_device(user, request)
        log_login_attempt(user, request, True, method='sms_otp')
        
        refresh = RefreshToken.for_user(user)
        return Response({
            "user_id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "user_type": user.user_type,
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "next_step": "complete"
        })


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            # Return success to prevent email enumeration
            return Response({
                "message": "If an account exists, a reset code has been sent."
            }, status=status.HTTP_200_OK)
        
        # Check rate limit
        can_send, remaining = check_otp_rate_limit(user.id, 'password_reset')
        if not can_send:
            return Response({
                "detail": "Daily limit reached."
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        otp_secret = generate_totp_secret()
        user.password_reset_otp_secret = otp_secret
        user.password_reset_otp_expires = timezone.now() + timezone.timedelta(minutes=OTP_EXPIRY_MINUTES)
        user.save()
        
        code = generate_totp_otp(otp_secret)
        send_email_otp(user.email, code, action='password_reset')
        increment_otp_count(user.id, 'password_reset')
        
        log_password_reset(user, request, 'request')
        
        return Response({
            "message": "Reset code sent to your email."
        }, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')
        new_password = request.data.get('password')
        
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({"detail": "Invalid request."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not user.password_reset_otp_secret or not user.password_reset_otp_expires:
            return Response({"detail": "No pending reset request."}, status=status.HTTP_400_BAD_REQUEST)
        
        if timezone.now() > user.password_reset_otp_expires:
            return Response({"detail": "Code expired."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not verify_totp_otp(user.password_reset_otp_secret, otp):
            return Response({"detail": "Invalid code."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Reset password
        user.set_password(new_password)
        user.password_reset_otp_secret = None
        user.password_reset_otp_expires = None
        user.save()
        
        log_password_reset(user, request, 'confirm')
        
        return Response({
            "message": "Password reset successfully."
        }, status=status.HTTP_200_OK)


class Setup2FAView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        # Generate secret
        secret = generate_totp_secret()
        user.totp_secret = secret
        user.save()
        
        # Generate QR code
        qr_code = generate_qr_code(secret, user.email)
        
        # Send QR via email as backup
        send_2fa_qr_code(user.email, secret, qr_code)
        
        log_2fa_activity(user, request, 'setup_init')
        
        return Response({
            "secret": secret,
            "qr_code": qr_code,
            "message": "Scan QR code or enter secret in authenticator app."
        })


class Confirm2FASetupView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        otp = request.data.get('otp')
        
        if not user.totp_secret:
            return Response({"detail": "2FA setup not initiated."}, status=status.HTTP_400_BAD_REQUEST)
        
        if verify_totp_otp(user.totp_secret, otp):
            user.totp_enabled = True
            user.totp_verified = True
            user.save()
            
            log_2fa_activity(user, request, 'setup_complete')
            return Response({"message": "2FA enabled successfully."})
        
        return Response({"detail": "Invalid code."}, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            log_user_activity(request.user, 'logout', request)
            
            return Response({
                "message": "Logout successful."
            }, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return Response({
                "error": "Invalid token."
            }, status=status.HTTP_400_BAD_REQUEST)


# ViewSets for user management
class CustomUserViewSet(ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAdminUser]


class LecturerViewSet(ModelViewSet):
    queryset = Lecturer.objects.all()
    serializer_class = LecturerSerializer
    permission_classes = [IsAuthenticated]


class OrgStaffViewSet(ModelViewSet):
    queryset = OrgStaff.objects.all()
    serializer_class = OrgStaffSerializer
    permission_classes = [IsAuthenticated]


class StudentAdminViewSet(ModelViewSet):
    queryset = StudentAdmin.objects.all()
    serializer_class = StudentAdminSerializer
    permission_classes = [IsAuthenticated]


class OrgAdminViewSet(ModelViewSet):
    queryset = OrgAdmin.objects.all()
    serializer_class = OrgAdminSerializer
    permission_classes = [IsAuthenticated]


class InstAdminViewSet(ModelViewSet):
    queryset = InstAdmin.objects.all()
    serializer_class = InstAdminSerializer
    permission_classes = [IsAuthenticated]


class InstStaffViewSet(ModelViewSet):
    queryset = InstStaff.objects.all()
    serializer_class = InstStaffSerializer
    permission_classes = [IsAuthenticated]


class ProfileViewSet(ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
