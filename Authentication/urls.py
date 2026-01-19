"""
Authentication URL Configuration - Fixed and Complete
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from Authentication.views import (
    RegisterView, VerifyView, LoginView, LogoutView, LoginVerifyView,
    ResendOTPView,
    PasswordResetRequestView, PasswordResetConfirmView,
    CustomUserViewSet, LecturerViewSet, OrgStaffViewSet,
    StudentAdminViewSet, OrgAdminViewSet, InstAdminViewSet,
    InstStaffViewSet, ProfileViewSet
)
from Authentication.views_extra import (
    ChangePasswordView, UpdateProfileView,
    DeviceListView, DeviceRevokeView,
    ActivityLogView, UserListView,
    GoogleLoginCallbackView
)

router = DefaultRouter()
router.register(r'users', CustomUserViewSet)
router.register(r'lecturers', LecturerViewSet)
router.register(r'org-staff', OrgStaffViewSet)
router.register(r'student-admins', StudentAdminViewSet)
router.register(r'org-admins', OrgAdminViewSet)
router.register(r'inst-admins', InstAdminViewSet)
router.register(r'inst-staff', InstStaffViewSet)
router.register(r'profiles', ProfileViewSet)

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
    
    # Core Authentication
    path('register/', RegisterView.as_view(), name='register'),
    path('verify/', VerifyView.as_view(), name='verify'),
    path('login/', LoginView.as_view(), name='login'),
    path('login-verify/', LoginVerifyView.as_view(), name='login-verify'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    
    # Password Reset
    path('password-reset-request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    
    # Profile & Account Management
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('update-profile/', UpdateProfileView.as_view(), name='update-profile'),
    
    # Device Management
    path('devices/', DeviceListView.as_view(), name='device-list'),
    path('devices/<int:device_id>/revoke/', DeviceRevokeView.as_view(), name='device-revoke'),
    
    # Activity Logs
    path('activity/', ActivityLogView.as_view(), name='activity-log'),
    
    # User List (Admin)
    path('user-list/', UserListView.as_view(), name='user-list'),
    
    # Social Auth Callbacks (JWT token conversion)
    path('google/callback/', GoogleLoginCallbackView.as_view(), name='google-callback'),
]
