"""
Additional Authentication Views
Password change, profile update, device management, activity logs, and social auth callbacks
"""
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import update_session_auth_hash
from django.conf import settings
from django.shortcuts import redirect
import logging

from Authentication.models import CustomUser, Profile, RoleChangeRequest
from Authentication.serializers import CustomUserSerializer, ProfileSerializer, RoleChangeRequestSerializer
from Authentication.device_utils import get_user_devices, revoke_device
from Authentication.activity_logger import log_user_activity, get_user_activity_logs

logger = logging.getLogger(__name__)


class ChangePasswordView(APIView):
    """Change password for authenticated user"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        # Accept both 'old_password' and 'current_password' field names
        old_password = request.data.get('old_password') or request.data.get('current_password')
        new_password = request.data.get('new_password')
        
        if not old_password or not new_password:
            return Response(
                {'detail': 'Both old and new password are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not user.check_password(old_password):
            return Response(
                {'detail': 'Current password is incorrect.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(new_password) < 8:
            return Response(
                {'detail': 'Password must be at least 8 characters.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)
        
        log_user_activity(user, 'password_change', request)
        
        return Response({'message': 'Password changed successfully.'})


class UpdateProfileView(APIView):
    """Update user profile information"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get current user profile"""
        user = request.user
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            profile = Profile.objects.create(user=user)
        
        return Response({
            'user': CustomUserSerializer(user).data,
            'profile': ProfileSerializer(profile).data
        })
    
    def patch(self, request):
        """Update profile fields"""
        user = request.user
        
        # Update user fields
        user_fields = ['first_name', 'last_name', 'phone_number']
        for field in user_fields:
            if field in request.data:
                setattr(user, field, request.data[field])
        user.save()
        
        # Update profile fields
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            profile = Profile.objects.create(user=user)
        
        profile_fields = ['bio', 'avatar', 'date_of_birth', 'location']
        for field in profile_fields:
            if field in request.data:
                setattr(profile, field, request.data[field])
        profile.save()
        
        log_user_activity(user, 'profile_update', request)
        
        return Response({
            'message': 'Profile updated successfully.',
            'user': CustomUserSerializer(user).data,
            'profile': ProfileSerializer(profile).data
        })


class DeviceListView(APIView):
    """List all devices for authenticated user"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        devices = get_user_devices(request.user)
        return Response({'devices': devices})


class DeviceRevokeView(APIView):
    """Revoke a specific device"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, device_id):
        success = revoke_device(request.user, device_id, request)
        
        if success:
            return Response({'message': 'Device revoked successfully.'})
        return Response(
            {'detail': 'Device not found or already revoked.'},
            status=status.HTTP_404_NOT_FOUND
        )


class ActivityLogView(APIView):
    """Get activity logs for authenticated user"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        limit = int(request.query_params.get('limit', 50))
        logs = get_user_activity_logs(request.user, limit=limit)
        return Response({'activities': logs})


class UserListView(APIView):
    """List all users (Admin only)"""
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        users = CustomUser.objects.all()
        serializer = CustomUserSerializer(users, many=True)
        return Response({'users': serializer.data})


class RoleChangeRequestView(APIView):
    """Submit or view role change requests"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get user's own role change requests"""
        requests = RoleChangeRequest.objects.filter(user=request.user).order_by('-created_at')
        serializer = RoleChangeRequestSerializer(requests, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """Submit a new role change request"""
        requested_role = request.data.get('requested_role')
        reason = request.data.get('reason')
        supporting_documents = request.data.get('supporting_documents', '')
        
        if not requested_role or not reason:
            return Response(
                {'detail': 'Requested role and reason are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user already has a pending request
        existing_request = RoleChangeRequest.objects.filter(
            user=request.user,
            status='pending'
        ).first()
        
        if existing_request:
            return Response(
                {'detail': 'You already have a pending role change request.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        role_request = RoleChangeRequest.objects.create(
            user=request.user,
            current_role=request.user.user_type,
            requested_role=requested_role,
            reason=reason,
            supporting_documents=supporting_documents
        )
        
        log_user_activity(request.user, 'role_change_request', request, f"Requested: {requested_role}")
        
        return Response(
            RoleChangeRequestSerializer(role_request).data,
            status=status.HTTP_201_CREATED
        )


class RoleChangeRequestListView(APIView):
    """Admin view to manage role change requests"""
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        """List all role change requests (Admin only)"""
        status_filter = request.query_params.get('status', None)
        requests = RoleChangeRequest.objects.all().order_by('-created_at')
        
        if status_filter:
            requests = requests.filter(status=status_filter)
        
        serializer = RoleChangeRequestSerializer(requests, many=True)
        return Response(serializer.data)
    
    def patch(self, request, pk=None):
        """Approve or reject a role change request (Admin only)"""
        if not pk:
            return Response(
                {'detail': 'Request ID is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            role_request = RoleChangeRequest.objects.get(pk=pk)
        except RoleChangeRequest.DoesNotExist:
            return Response(
                {'detail': 'Role change request not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        new_status = request.data.get('status')
        admin_notes = request.data.get('admin_notes', '')
        
        if new_status not in ['approved', 'rejected']:
            return Response(
                {'detail': 'Invalid status. Must be "approved" or "rejected".'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        role_request.status = new_status
        role_request.admin_notes = admin_notes
        role_request.reviewed_by = request.user
        role_request.save()
        
        # If approved, update user's role
        if new_status == 'approved':
            user = role_request.user
            user.user_type = role_request.requested_role
            user.save()
            log_user_activity(user, 'role_changed', request, f"New role: {role_request.requested_role}")
        
        return Response(RoleChangeRequestSerializer(role_request).data)


# ============================================
# Social Auth Callback Views
# These convert allauth sessions to JWT tokens
# ============================================

class BaseSocialCallbackView(APIView):
    """Base class for social auth callbacks"""
    permission_classes = []
    
    def get(self, request):
        """Handle OAuth callback and return JWT tokens"""
        # Check if user is authenticated via allauth session
        if request.user.is_authenticated:
            user = request.user
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Get frontend URL (ensure no double slashes)
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173/')
            if not frontend_url.endswith('/'):
                frontend_url += '/'
            
            # Check profile completion status
            profile_completed = getattr(user, 'profile_completed', True)
            
            # Build redirect URL with tokens and user info
            redirect_url = (
                f"{frontend_url}auth/callback?"
                f"access_token={str(refresh.access_token)}"
                f"&refresh_token={str(refresh)}"
                f"&user_id={user.id}"
                f"&email={user.email or ''}"
                f"&first_name={user.first_name or ''}"
                f"&user_type={user.user_type or ''}"
                f"&profile_completed={'true' if profile_completed else 'false'}"
            )
            
            log_user_activity(user, 'social_login', request, f"Provider: {self.provider}")
            
            return redirect(redirect_url)
        
        # If not authenticated, redirect to login with error
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173/')
        if not frontend_url.endswith('/'):
            frontend_url += '/'
        return redirect(f"{frontend_url}login?error=auth_failed")


class GoogleLoginCallbackView(BaseSocialCallbackView):
    """Handle Google OAuth callback"""
    provider = 'google'


class FacebookLoginCallbackView(BaseSocialCallbackView):
    """Handle Facebook OAuth callback"""
    provider = 'facebook'


class GitHubLoginCallbackView(BaseSocialCallbackView):
    """Handle GitHub OAuth callback"""
    provider = 'github'


class AppleLoginCallbackView(BaseSocialCallbackView):
    """Handle Apple OAuth callback"""
    provider = 'apple'


class TwitterLoginCallbackView(BaseSocialCallbackView):
    """Handle Twitter/X OAuth callback"""
    provider = 'twitter'


class LinkedInLoginCallbackView(BaseSocialCallbackView):
    """Handle LinkedIn OAuth callback"""
    provider = 'linkedin'


class MicrosoftLoginCallbackView(BaseSocialCallbackView):
    """Handle Microsoft OAuth callback"""
    provider = 'microsoft'
