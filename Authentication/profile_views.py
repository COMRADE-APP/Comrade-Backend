"""
Profile and Account Management Views
Handles user profiles, account deactivation, deletion requests, and admin review
"""
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta, date
import json
import logging

from Authentication.models import (
    CustomUser, UserProfile, AccountDeletionRequest, ArchivedUserData
)
from Authentication.serializers import (
    UserProfileSerializer, UserProfileUpdateSerializer,
    AccountDeletionRequestSerializer, ArchivedUserDataSerializer,
    CustomUserSerializer
)
from Authentication.activity_logger import log_user_activity

logger = logging.getLogger(__name__)


class CheckEmailView(APIView):
    """Check if email exists (for registration validation)"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'detail': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        exists = CustomUser.objects.filter(email=email).exists()
        return Response({
            'exists': exists,
            'available': not exists
        })


class UserProfileView(APIView):
    """Get or update current user's profile"""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get(self, request):
        """Get current user's profile"""
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)
    
    def patch(self, request):
        """Update current user's profile"""
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileUpdateSerializer(profile, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            log_user_activity(request.user, 'profile_update', request, 'Profile updated')
            
            # Return full profile data
            full_serializer = UserProfileSerializer(profile, context={'request': request})
            return Response(full_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileDetailView(APIView):
    """Get a specific user's profile (respects privacy settings)"""
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get(self, request, user_id):
        user = get_object_or_404(CustomUser, id=user_id, account_status='active')
        profile, created = UserProfile.objects.get_or_create(user=user)
        serializer = UserProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)


class UploadAvatarView(APIView):
    """Upload/update avatar image"""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        if 'avatar' not in request.FILES:
            return Response({'detail': 'No image provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        profile.avatar = request.FILES['avatar']
        profile.save()
        
        log_user_activity(request.user, 'avatar_update', request, 'Avatar updated')
        
        serializer = UserProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)
    
    def delete(self, request):
        profile = get_object_or_404(UserProfile, user=request.user)
        if profile.avatar:
            profile.avatar.delete()
            profile.save()
        return Response({'message': 'Avatar removed'})


class UploadCoverView(APIView):
    """Upload/update cover image"""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        if 'cover' not in request.FILES:
            return Response({'detail': 'No image provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        profile.cover_image = request.FILES['cover']
        profile.save()
        
        log_user_activity(request.user, 'cover_update', request, 'Cover image updated')
        
        serializer = UserProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)
    
    def delete(self, request):
        profile = get_object_or_404(UserProfile, user=request.user)
        if profile.cover_image:
            profile.cover_image.delete()
            profile.save()
        return Response({'message': 'Cover removed'})


class ProfileSetupView(APIView):
    """Complete profile setup after registration - creates user type profiles"""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        user = request.user
        
        # Get or create UserProfile
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        # Update profile fields
        profile.bio = request.data.get('bio', profile.bio or '')
        profile.location = request.data.get('location', profile.location or '')
        profile.occupation = request.data.get('occupation', profile.occupation or '')
        profile.website = request.data.get('website', profile.website or '')
        
        # Handle interests - can be string or list
        interests = request.data.get('interests', [])
        if isinstance(interests, str):
            interests = [i.strip() for i in interests.split(',') if i.strip()]
        profile.interests = interests
        
        # Handle avatar upload
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']
        
        # Handle cover upload
        if 'cover' in request.FILES:
            profile.cover_image = request.FILES['cover']
        
        profile.save()
        
        # Mark profile as completed
        user.profile_completed = True
        user.save()
        
        # Create user type-specific profile based on user_type
        user_type_profile = self._create_user_type_profile(user, request.data)
        
        log_user_activity(user, 'profile_setup_complete', request, 'Profile setup completed')
        
        serializer = UserProfileSerializer(profile, context={'request': request})
        return Response({
            'message': 'Profile setup completed successfully',
            'profile': serializer.data,
            'user_type_profile_created': user_type_profile is not None
        })
    
    def _create_user_type_profile(self, user, data):
        """Create user type-specific profile (Lecturer, Student, etc.)"""
        from Authentication.models import (
            Lecturer, Student, OrgStaff, InstStaff, NormalUser
        )
        
        user_type = user.user_type
        
        try:
            if user_type == 'lecturer':
                # Check if Lecturer already exists
                if not hasattr(user, 'lecturer'):
                    lecturer = Lecturer.objects.create(
                        user=user,
                        lecturer_id=f"LCT{user.id:06d}",
                        faculty=data.get('faculty', 'General'),
                        department=data.get('department', 'General'),
                    )
                    return lecturer
                    
            elif user_type == 'student':
                # Check if Student already exists
                if not hasattr(user, 'student'):
                    from Authentication.models import Institution
                    institution = Institution.objects.first()  # Default institution
                    student = Student.objects.create(
                        user=user,
                        admission_number=data.get('admission_number', f"STD{user.id:06d}"),
                        year_of_admission=data.get('year_of_admission', 2024),
                        year_of_study=data.get('year_of_study', 1),
                        institution=institution,
                        course=data.get('course', 'General Studies'),
                        expecte_year_of_graduation=data.get('expected_graduation', 2028),
                    )
                    return student
                    
            elif user_type == 'normal_user':
                if not hasattr(user, 'normaluser'):
                    normal_user = NormalUser.objects.create(user=user)
                    return normal_user
                    
        except Exception as e:
            logger.error(f"Error creating user type profile: {e}")
            
        return None


class DeactivateAccountView(APIView):
    """Deactivate user account (reversible)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        if user.account_status != 'active':
            return Response({
                'detail': f'Account is already {user.account_status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.account_status = 'deactivated'
        user.deactivated_at = timezone.now()
        user.save()
        
        log_user_activity(user, 'account_deactivated', request, 'Account deactivated by user')
        
        return Response({
            'message': 'Account deactivated. You can reactivate by logging in again.',
            'account_status': 'deactivated'
        })


class ReactivateAccountView(APIView):
    """Reactivate a deactivated account"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if user.account_status != 'deactivated':
            return Response({
                'detail': 'Account is not deactivated',
                'account_status': user.account_status
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not user.check_password(password):
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        
        user.account_status = 'active'
        user.deactivated_at = None
        user.save()
        
        log_user_activity(user, 'account_reactivated', request, 'Account reactivated')
        
        return Response({
            'message': 'Account reactivated successfully. Please login.',
            'account_status': 'active'
        })


class RequestDeletionView(APIView):
    """Request account deletion (60-day review period)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        reason = request.data.get('reason', '')
        
        if not reason:
            return Response({'detail': 'Please provide a reason for deletion'}, status=status.HTTP_400_BAD_REQUEST)
        
        if user.account_status == 'pending_deletion':
            return Response({
                'detail': 'Deletion request already pending',
                'request': AccountDeletionRequestSerializer(
                    user.deletion_requests.filter(status='pending').first()
                ).data
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create deletion request
        deletion_request = AccountDeletionRequest.objects.create(
            user=user,
            email=user.email,
            user_type=user.user_type,
            reason=reason,
            scheduled_deletion_date=date.today() + timedelta(days=60)
        )
        
        # Update user status
        user.account_status = 'pending_deletion'
        user.deletion_requested_at = timezone.now()
        user.deletion_reason = reason
        user.save()
        
        log_user_activity(user, 'deletion_requested', request, 'Account deletion requested')
        
        return Response({
            'message': 'Deletion request submitted. Account will be reviewed within 60 days.',
            'request_id': deletion_request.id,
            'scheduled_deletion_date': deletion_request.scheduled_deletion_date.isoformat()
        }, status=status.HTTP_201_CREATED)


class CancelDeletionView(APIView):
    """Cancel pending deletion request"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        if user.account_status != 'pending_deletion':
            return Response({
                'detail': 'No pending deletion request'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Cancel pending requests
        user.deletion_requests.filter(status='pending').update(
            status='cancelled'
        )
        
        # Restore account
        user.account_status = 'active'
        user.deletion_requested_at = None
        user.deletion_reason = ''
        user.save()
        
        log_user_activity(user, 'deletion_cancelled', request, 'Account deletion cancelled')
        
        return Response({
            'message': 'Deletion request cancelled. Account restored.',
            'account_status': 'active'
        })


class DeletionRequestViewSet(viewsets.ModelViewSet):
    """Admin viewset for managing deletion requests"""
    serializer_class = AccountDeletionRequestSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        queryset = AccountDeletionRequest.objects.all()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve deletion request and archive user data"""
        deletion_request = self.get_object()
        
        if deletion_request.status != 'pending':
            return Response({
                'detail': f'Request is already {deletion_request.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = deletion_request.user
        notes = request.data.get('notes', '')
        
        # Archive user data before deletion
        if user:
            user_data = {
                'first_name': user.first_name,
                'last_name': user.last_name,
                'other_names': user.other_names,
                'email': user.email,
                'phone_number': user.phone_number,
                'user_type': user.user_type,
                'date_joined': user.date_joined.isoformat() if user.date_joined else None,
            }
            
            # Get profile data
            try:
                profile = user.user_profile
                user_data['profile'] = {
                    'bio': profile.bio,
                    'location': profile.location,
                    'occupation': profile.occupation,
                    'interests': profile.interests,
                }
            except UserProfile.DoesNotExist:
                pass
            
            # Create archive
            ArchivedUserData.objects.create(
                original_user_id=user.id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                user_type=user.user_type,
                user_data=user_data,
                activity_summary={},  # Could pull from activity logs
                deletion_reason=deletion_request.reason,
                deletion_request_id=deletion_request.id,
                archived_by=request.user
            )
            
            # Mark user as deleted (soft delete)
            user.account_status = 'deleted'
            user.is_active = False
            user.save()
        
        # Update request
        deletion_request.status = 'approved'
        deletion_request.reviewed_by = request.user
        deletion_request.reviewed_at = timezone.now()
        deletion_request.review_notes = notes
        deletion_request.save()
        
        return Response({
            'message': 'Deletion approved. User data archived.',
            'request': AccountDeletionRequestSerializer(deletion_request).data
        })
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject deletion request"""
        deletion_request = self.get_object()
        
        if deletion_request.status != 'pending':
            return Response({
                'detail': f'Request is already {deletion_request.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        notes = request.data.get('notes', '')
        
        # Update request
        deletion_request.status = 'rejected'
        deletion_request.reviewed_by = request.user
        deletion_request.reviewed_at = timezone.now()
        deletion_request.review_notes = notes
        deletion_request.save()
        
        # Restore user if they exist
        user = deletion_request.user
        if user and user.account_status == 'pending_deletion':
            user.account_status = 'active'
            user.deletion_requested_at = None
            user.deletion_reason = ''
            user.save()
        
        return Response({
            'message': 'Deletion request rejected. Account restored.',
            'request': AccountDeletionRequestSerializer(deletion_request).data
        })


class ArchivedUserViewSet(viewsets.ReadOnlyModelViewSet):
    """Admin viewset for viewing archived user data"""
    queryset = ArchivedUserData.objects.all()
    serializer_class = ArchivedUserDataSerializer
    permission_classes = [permissions.IsAdminUser]


class UserSearchView(APIView):
    """Search for users by name or email (for messaging, following, etc.)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if len(query) < 2:
            return Response([])
        
        from django.db.models import Q, Value
        from django.db.models.functions import Concat
        
        users = CustomUser.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        ).exclude(id=request.user.id).filter(is_active=True)[:20]
        
        results = []
        for u in users:
            avatar_url = None
            try:
                if hasattr(u, 'user_profile') and u.user_profile.avatar:
                    avatar_url = request.build_absolute_uri(u.user_profile.avatar.url)
            except:
                pass
            
            results.append({
                'id': u.id,
                'first_name': u.first_name,
                'last_name': u.last_name,
                'full_name': f"{u.first_name or ''} {u.last_name or ''}".strip() or u.email,
                'email': u.email,
                'avatar_url': avatar_url,
                'user_type': u.user_type
            })
        
        return Response(results)

