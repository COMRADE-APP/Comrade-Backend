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
    InstAdmin, InstStaff, Profile
)
from Authentication.serializers import (
    LoginSerializer, CustomUserSerializer, LecturerSerializer, OrgStaffSerializer, 
    StudentAdminSerializer, OrgAdminSerializer, InstAdminSerializer, 
    InstStaffSerializer, ProfileSerializer, BaseUserSerializer
)
from Authentication.otp_utils import (
    send_email_otp, check_otp_rate_limit, increment_otp_count, 
    OTP_EXPIRY_MINUTES
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
    authentication_classes = []
    
    def post(self, request):
        serializer = BaseUserSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
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
            
            # Create Profile automatically
            Profile.objects.get_or_create(user=user)
            
            log_user_activity(user, 'register', request, "User registered and activated")
            
            return Response({
                "message": "Registration successful. Please log in to continue.",
                "user_id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "user_type": user.user_type,
                "next_step": "login"
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyView(APIView):
    """Email verification via link (optional)"""
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
            user.save()
            return Response({'detail': 'Email verified successfully.'})
        
        return Response({'detail': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        user = authenticate(email=email, password=password)
        
        if user is None:
            log_login_attempt(None, request, False, "Invalid credentials")
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.is_active:
            return Response({
                "detail": "Account is not active."
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Generate and send Email OTP
        otp_code = str(secrets.SystemRandom().randint(100000, 999999))
        user.login_otp = otp_code
        user.login_otp_expires = timezone.now() + timezone.timedelta(minutes=OTP_EXPIRY_MINUTES)
        user.save()
        
        email_sent = send_email_otp(user.email, otp_code, action='login')
        
        if not email_sent:
            return Response({
                "detail": "Failed to send verification code."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            "message": "Verification code sent to your email.",
            "email": user.email,
            "verification_required": True,
            "next_step": "verify_email_otp",
            "otp_method": "email"
        })


@method_decorator(csrf_exempt, name='dispatch')
class LoginVerifyView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')
        
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        
        if not user.login_otp or not user.login_otp_expires:
            return Response({"detail": "No pending verification found."}, status=status.HTTP_400_BAD_REQUEST)
        
        if timezone.now() > user.login_otp_expires:
            return Response({"detail": "Verification code expired."}, status=status.HTTP_400_BAD_REQUEST)
        
        if otp != user.login_otp:
            return Response({"detail": "Invalid verification code."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Clear OTP
        user.login_otp = None
        user.login_otp_expires = None
        user.save()
        
        # Complete login
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
    authentication_classes = []
    
    def post(self, request):
        email = request.data.get('email')
        
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
        user.login_otp = otp_code
        user.login_otp_expires = timezone.now() + timezone.timedelta(minutes=OTP_EXPIRY_MINUTES)
        user.save()
        
        if send_email_otp(user.email, otp_code, action='login'):
            return Response({'message': 'Verification code resent to your email.'}, status=status.HTTP_200_OK)
                
        return Response({'detail': 'Failed to send.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({
                "message": "If an account exists, a reset code has been sent."
            }, status=status.HTTP_200_OK)
        
        otp_code = str(secrets.SystemRandom().randint(100000, 999999))
        user.login_otp = otp_code # Using login_otp for simplicity or restore password_reset_otp
        user.login_otp_expires = timezone.now() + timezone.timedelta(minutes=OTP_EXPIRY_MINUTES)
        user.save()
        
        send_email_otp(user.email, otp_code, action='password_reset')
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
        
        if not user.login_otp or not user.login_otp_expires:
            return Response({"detail": "No pending reset request."}, status=status.HTTP_400_BAD_REQUEST)
        
        if timezone.now() > user.login_otp_expires:
            return Response({"detail": "Code expired."}, status=status.HTTP_400_BAD_REQUEST)
        
        if user.login_otp != otp:
            return Response({"detail": "Invalid code."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Reset password
        user.set_password(new_password)
        user.login_otp = None
        user.login_otp_expires = None
        user.save()
        
        log_password_reset(user, request, 'confirm')
        
        return Response({
            "message": "Password reset successfully."
        }, status=status.HTTP_200_OK)


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
