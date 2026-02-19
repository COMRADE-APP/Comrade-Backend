"""
Authentication URL Configuration - Fixed and Complete
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from Authentication.views_totp import (
    TOTPSetupView, TOTPVerifySetupView,
    TOTPVerifyLoginView, TOTPDisableView, TOTPBackupCodesView
)
from Authentication.views import (
    RegisterView, VerifyView, LoginView, LogoutView, LoginVerifyView,
    RegisterVerifyView, HeartbeatView,
    PasswordResetRequestView, PasswordResetConfirmView,
    Setup2FAView, Confirm2FASetupView,
    ResendOTPView, VerifySMSOTPView, Verify2FAView,
    CustomUserViewSet, LecturerViewSet, OrgStaffViewSet,
    StudentAdminViewSet, OrgAdminViewSet, InstAdminViewSet,
    InstStaffViewSet, ProfileViewSet, MeView
)
from Authentication.views_extra import (
    ChangePasswordView, UpdateProfileView,
    DeviceListView, DeviceRevokeView,
    ActivityLogView, UserListView,
    RoleChangeRequestView, RoleChangeRequestListView,
    GoogleLoginCallbackView, FacebookLoginCallbackView,
    GitHubLoginCallbackView, AppleLoginCallbackView,
    TwitterLoginCallbackView, LinkedInLoginCallbackView,
    MicrosoftLoginCallbackView
)
from Authentication.profile_views import (
    CheckEmailView, UserProfileView, UserProfileDetailView,
    UploadAvatarView, UploadCoverView, ProfileSetupView,
    DeactivateAccountView, ReactivateAccountView,
    RequestDeletionView, CancelDeletionView,
    DeletionRequestViewSet, ArchivedUserViewSet, UserSearchView
)
from Authentication.admin_views import (
    AdminDashboardStatsView, AdminUserManagementView,
    AdminToggleUserActiveView, AdminUpdateUserRoleView,
    AdminContentModerationView, AdminContentDeleteView,
    AdminAnalyticsView, AdminSystemInfoView
)
from Authentication.role_portal_views import (
    StaffPortalDashboardView, StaffUserAssistView,
    AuthorPortalDashboardView,
    ModeratorPortalDashboardView, ModeratorContentReviewView,
    LecturerPortalDashboardView,
    InstitutionPortalDashboardView,
    OrganisationPortalDashboardView,
    PartnerPortalDashboardView
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

# Admin routers
router.register(r'admin/deletion-requests', DeletionRequestViewSet, basename='deletion-requests')
router.register(r'admin/archived-users', ArchivedUserViewSet, basename='archived-users')

urlpatterns = [
    # Django allauth URLs (includes social login URLs)
    path('', include('allauth.urls')),
    
    # Router URLs
    path('', include(router.urls)),
    
    # Core Authentication
    path('register/', RegisterView.as_view(), name='register'),
    path('register-verify/', RegisterVerifyView.as_view(), name='register-verify'),
    path('verify/', VerifyView.as_view(), name='verify'),
    path('login/', LoginView.as_view(), name='login'),
    path('login-verify/', LoginVerifyView.as_view(), name='login-verify'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    path('check-email/', CheckEmailView.as_view(), name='check-email'),
    path('me/', MeView.as_view(), name='me'),
    path('heartbeat/', HeartbeatView.as_view(), name='heartbeat'),
    
    # 2FA/OTP Verification
    path('verify-2fa/', Verify2FAView.as_view(), name='verify-2fa'),
    path('verify-sms-otp/', VerifySMSOTPView.as_view(), name='verify-sms-otp'),
    path('setup-2fa/', Setup2FAView.as_view(), name='setup-2fa'),
    path('confirm-2fa-setup/', Confirm2FASetupView.as_view(), name='confirm-2fa-setup'),
    
    # TOTP/Authenticator App
    path('totp/setup/', TOTPSetupView.as_view(), name='totp-setup'),
    path('totp/verify-setup/', TOTPVerifySetupView.as_view(), name='totp-verify-setup'),
    path('totp/verify-login/', TOTPVerifyLoginView.as_view(), name='totp-verify-login'),
    path('totp/disable/', TOTPDisableView.as_view(), name='totp-disable'),
    path('totp/backup-codes/', TOTPBackupCodesView.as_view(), name='totp-backup-codes'),
    
    # Password Reset
    path('password-reset-request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    
    # Profile & Account Management
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('update-profile/', UpdateProfileView.as_view(), name='update-profile'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('profile/<int:user_id>/', UserProfileDetailView.as_view(), name='user-profile-detail'),
    path('profile/avatar/', UploadAvatarView.as_view(), name='upload-avatar'),
    path('profile/cover/', UploadCoverView.as_view(), name='upload-cover'),
    path('profile-setup/', ProfileSetupView.as_view(), name='profile-setup'),
    
    # Account Management
    path('account/deactivate/', DeactivateAccountView.as_view(), name='deactivate-account'),
    path('account/reactivate/', ReactivateAccountView.as_view(), name='reactivate-account'),
    path('account/request-deletion/', RequestDeletionView.as_view(), name='request-deletion'),
    path('account/cancel-deletion/', CancelDeletionView.as_view(), name='cancel-deletion'),
    
    # Device Management
    path('devices/', DeviceListView.as_view(), name='device-list'),
    path('devices/<int:device_id>/revoke/', DeviceRevokeView.as_view(), name='device-revoke'),
    
    # Activity Logs
    path('activity/', ActivityLogView.as_view(), name='activity-log'),
    
    # User List (Admin)
    path('user-list/', UserListView.as_view(), name='user-list'),
    
    # User Search
    path('users/search/', UserSearchView.as_view(), name='user-search'),
    
    # Role Change Requests
    path('role-change-request/', RoleChangeRequestView.as_view(), name='role-change-request'),
    path('role-change-requests/', RoleChangeRequestListView.as_view(), name='role-change-requests'),
    path('role-change-requests/<int:pk>/', RoleChangeRequestListView.as_view(), name='role-change-request-detail'),
    
    # Social Auth Callbacks (JWT token conversion)
    path('google/callback/', GoogleLoginCallbackView.as_view(), name='google-callback'),
    path('facebook/callback/', FacebookLoginCallbackView.as_view(), name='facebook-callback'),
    path('github/callback/', GitHubLoginCallbackView.as_view(), name='github-callback'),
    path('apple/callback/', AppleLoginCallbackView.as_view(), name='apple-callback'),
    path('twitter/callback/', TwitterLoginCallbackView.as_view(), name='twitter-callback'),
    path('linkedin/callback/', LinkedInLoginCallbackView.as_view(), name='linkedin-callback'),
    path('microsoft/callback/', MicrosoftLoginCallbackView.as_view(), name='microsoft-callback'),
    
    # Admin Portal API
    path('admin/dashboard-stats/', AdminDashboardStatsView.as_view(), name='admin-dashboard-stats'),
    path('admin/users-management/', AdminUserManagementView.as_view(), name='admin-users-management'),
    path('admin/users/<int:user_id>/toggle-active/', AdminToggleUserActiveView.as_view(), name='admin-toggle-user'),
    path('admin/users/<int:user_id>/update-role/', AdminUpdateUserRoleView.as_view(), name='admin-update-role'),
    path('admin/content/', AdminContentModerationView.as_view(), name='admin-content-moderation'),
    path('admin/content/delete/', AdminContentDeleteView.as_view(), name='admin-content-delete'),
    path('admin/analytics/', AdminAnalyticsView.as_view(), name='admin-analytics'),
    path('admin/system-info/', AdminSystemInfoView.as_view(), name='admin-system-info'),

    # Role-Specific Portal APIs
    path('portal/staff/dashboard/', StaffPortalDashboardView.as_view(), name='staff-portal-dashboard'),
    path('portal/staff/users/', StaffUserAssistView.as_view(), name='staff-user-assist'),
    path('portal/author/dashboard/', AuthorPortalDashboardView.as_view(), name='author-portal-dashboard'),
    path('portal/moderator/dashboard/', ModeratorPortalDashboardView.as_view(), name='moderator-portal-dashboard'),
    path('portal/moderator/content/', ModeratorContentReviewView.as_view(), name='moderator-content-review'),
    path('portal/lecturer/dashboard/', LecturerPortalDashboardView.as_view(), name='lecturer-portal-dashboard'),
    path('portal/institution/dashboard/', InstitutionPortalDashboardView.as_view(), name='institution-portal-dashboard'),
    path('portal/organisation/dashboard/', OrganisationPortalDashboardView.as_view(), name='organisation-portal-dashboard'),
    path('portal/partner/dashboard/', PartnerPortalDashboardView.as_view(), name='partner-portal-dashboard'),
]

