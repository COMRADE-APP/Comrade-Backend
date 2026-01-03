from django.urls import path
from Authentication.views import (
    RegisterView, LoginView, LoginVerifyView, ResendOTPView, VerifyView, LogoutView, 
    PasswordResetRequestView, PasswordResetConfirmView,
    Setup2FAView, Confirm2FASetupView, Verify2FAView, VerifySMSOTPView,
    CustomUserViewSet, LecturerViewSet, OrgStaffViewSet, StudentAdminViewSet, 
    OrgAdminViewSet, InstAdminViewSet, InstStaffViewSet, ProfileViewSet
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'custom_users', CustomUserViewSet, basename='custom_user')
router.register(r'lecturers', LecturerViewSet, basename='lecturer')
router.register(r'org_staffs', OrgStaffViewSet, basename='org_staff')
router.register(r'student_admins', StudentAdminViewSet, basename='student_admin')
router.register(r'org_admins', OrgAdminViewSet, basename='org_admin')
router.register(r'inst_admins', InstAdminViewSet, basename='inst_admin')
router.register(r'inst_staffs', InstStaffViewSet,basename='inst_staff')
router.register(r'profiles', ProfileViewSet, basename='profile')

urlpatterns = [
    # Core Authentication
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('login-verify/', LoginVerifyView.as_view(), name='login_verify'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend_otp'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('verify/', VerifyView.as_view(), name='verify'),
    
    # Password Reset
    path('password-reset-request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    
    # 2FA / OTP
    path('setup-2fa/', Setup2FAView.as_view(), name='setup_2fa'),
    path('confirm-2fa-setup/', Confirm2FASetupView.as_view(), name='confirm_2fa_setup'),
    path('verify-2fa/', Verify2FAView.as_view(), name='verify_2fa'),
    path('verify-sms-otp/', VerifySMSOTPView.as_view(), name='verify_sms_otp'),
]

urlpatterns += router.urls
