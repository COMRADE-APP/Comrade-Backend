from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils import timezone
from .models import (
    CredentialVerification, UserQualification, BackgroundCheck,
    MembershipRequest, InvitationLink, PresetUserAccount
)
from .serializers import (
    CredentialVerificationSerializer, CredentialVerificationCreateSerializer,
    UserQualificationSerializer, BackgroundCheckSerializer,
    MembershipRequestSerializer, InvitationLinkSerializer,
    InvitationLinkCreateSerializer, PresetUserAccountSerializer,
    PresetUserAccountCreateSerializer
)


class CredentialVerificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for credential verification submissions and management
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Users can see their own submissions, admins can see all
        if user.is_staff or user.is_admin:
            return CredentialVerification.objects.all()
        return CredentialVerification.objects.filter(user=user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CredentialVerificationCreateSerializer
        return CredentialVerificationSerializer
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        """Approve a credential verification"""
        verification = self.get_object()
        verification.status = 'approved'
        verification.reviewed_by = request.user
        verification.reviewed_at = timezone.now()
        verification.approved_at = timezone.now()
        verification.save()
        
        serializer = self.get_serializer(verification)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reject(self, request, pk=None):
        """Reject a credential verification"""
        verification = self.get_object()
        verification.status = 'rejected'
        verification.reviewed_by = request.user
        verification.reviewed_at = timezone.now()
        verification.rejection_reason = request.data.get('rejection_reason', '')
        verification.save()
        
        serializer = self.get_serializer(verification)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def request_info(self, request, pk=None):
        """Request additional information"""
        verification = self.get_object()
        verification.status = 'additional_info_required'
        verification.reviewed_by = request.user
        verification.reviewed_at = timezone.now()
        verification.additional_info_request = request.data.get('additional_info_request', '')
        verification.save()
        
        serializer = self.get_serializer(verification)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_submissions(self, request):
        """Get current user's credential submissions"""
        submissions = CredentialVerification.objects.filter(user=request.user)
        serializer = self.get_serializer(submissions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def pending(self, request):
        """Get all pending verifications (admin only)"""
        pending = CredentialVerification.objects.filter(status='pending')
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)


class UserQualificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user qualifications
    """
    queryset = UserQualification.objects.all()
    serializer_class = UserQualificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_admin:
            return UserQualification.objects.all()
        return UserQualification.objects.filter(user=user)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def verify(self, request, pk=None):
        """Verify a qualification (admin only)"""
        qualification = self.get_object()
        qualification.verified = True
        qualification.verified_at = timezone.now()
        qualification.verified_by = request.user
        qualification.save()
        
        serializer = self.get_serializer(qualification)
        return Response(serializer.data)


class BackgroundCheckViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for background checks
    """
    queryset = BackgroundCheck.objects.all()
    serializer_class = BackgroundCheckSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_admin:
            return BackgroundCheck.objects.all()
        return BackgroundCheck.objects.filter(user=user)


class MembershipRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for membership requests
    """
    serializer_class = MembershipRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Users see their own requests, admins see all
        if user.is_staff or user.is_admin:
            return MembershipRequest.objects.all()
        return MembershipRequest.objects.filter(user=user)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        """Approve a membership request"""
        membership_request = self.get_object()
        membership_request.status = 'approved'
        membership_request.processed_by = request.user
        membership_request.processed_at = timezone.now()
        membership_request.save()
        
        # TODO: Actually add user to entity
        
        serializer = self.get_serializer(membership_request)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reject(self, request, pk=None):
        """Reject a membership request"""
        membership_request = self.get_object()
        membership_request.status = 'rejected'
        membership_request.processed_by = request.user
        membership_request.processed_at = timezone.now()
        membership_request.rejection_reason = request.data.get('rejection_reason', '')
        membership_request.save()
        
        serializer = self.get_serializer(membership_request)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def pending(self, request):
        """Get all pending requests"""
        entity_type = request.query_params.get('entity_type')
        entity_id = request.query_params.get('entity_id')
        
        queryset = MembershipRequest.objects.filter(status='pending')
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class InvitationLinkViewSet(viewsets.ModelViewSet):
    """
    ViewSet for invitation links
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Users see invites they created, admins see all
        if user.is_staff or user.is_admin:
            return InvitationLink.objects.all()
        return InvitationLink.objects.filter(created_by=user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return InvitationLinkCreateSerializer
        return InvitationLinkSerializer
    
    @action(detail=False, methods=['get'])
    def verify(self, request):
        """Verify an invitation token"""
        token = request.query_params.get('token')
        if not token:
            return Response({'error': 'Token required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            invitation = InvitationLink.objects.get(token=token)
            if not invitation.is_valid:
                return Response({'error': 'Invalid or expired invitation'}, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = self.get_serializer(invitation)
            return Response(serializer.data)
        except InvitationLink.DoesNotExist:
            return Response({'error': 'Invalid invitation token'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    def accept(self, request):
        """Accept an invitation"""
        token = request.data.get('token')
        if not token:
            return Response({'error': 'Token required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            invitation = InvitationLink.objects.get(token=token)
            if not invitation.is_valid:
                return Response({'error': 'Invalid or expired invitation'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Increment uses
            invitation.uses_count += 1
            invitation.save()
            
            # TODO: Actually add user to entity with role
            
            return Response({
                'message': 'Invitation accepted',
                'entity_type': invitation.entity_type,
                'entity_id': invitation.entity_id,
                'role': invitation.role_granted
            })
        except InvitationLink.DoesNotExist:
            return Response({'error': 'Invalid invitation token'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate an invitation link"""
        invitation = self.get_object()
        invitation.is_active = False
        invitation.save()
        
        serializer = self.get_serializer(invitation)
        return Response(serializer.data)


class PresetUserAccountViewSet(viewsets.ModelViewSet):
    """
    ViewSet for preset user accounts
    """
    permission_classes = [IsAdminUser]
    queryset = PresetUserAccount.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PresetUserAccountCreateSerializer
        return PresetUserAccountSerializer
    
    @action(detail=True, methods=['post'])
    def send_invitation(self, request, pk=None):
        """Send invitation email to preset account"""
        account = self.get_object()
        
        # TODO: Send actual email with credentials
        
        account.invitation_sent = True
        account.invitation_sent_at = timezone.now()
        account.save()
        
        serializer = self.get_serializer(account)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get all pending activations"""
        pending = PresetUserAccount.objects.filter(activated=False)
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)