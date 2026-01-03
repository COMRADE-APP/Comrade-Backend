from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404

from Verification.models import (
    InstitutionVerificationRequest,
    OrganizationVerificationRequest,
    VerificationDocument,
    EmailVerification,
    WebsiteVerification,
    VerificationActivity
)
from Verification.serializers import (
    InstitutionVerificationRequestSerializer,
    InstitutionVerificationRequestCreateSerializer,
    OrganizationVerificationRequestSerializer,
    OrganizationVerificationRequestCreateSerializer,
    VerificationDocumentSerializer,
    EmailVerificationSerializer,
    WebsiteVerificationSerializer,
    EmailVerificationCodeSerializer,
    WebsiteVerificationCheckSerializer
)
from Verification.verification_utils import (
    EmailVerifier,
    WebsiteVerifier,
    DocumentVerifier,
    VerificationWorkflow
)


class InstitutionVerificationViewSet(viewsets.ModelViewSet):
    """ViewSet for institution verification requests"""
    queryset = InstitutionVerificationRequest.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return InstitutionVerificationRequestCreateSerializer
        return InstitutionVerificationRequestSerializer
    
    def get_queryset(self):
        """Users can only see their own requests unless they're staff"""
        if self.request.user.is_staff:
            return InstitutionVerificationRequest.objects.all()
        return InstitutionVerificationRequest.objects.filter(submitter=self.request.user)
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create a new institution verification request"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create the request
        instance = serializer.save(
            submitter=request.user,
            status='draft'
        )
        
        # Create email verification
        email_verifier = EmailVerifier()
        email_verification = email_verifier.create_verification(
            instance, 'institution', instance.official_email
        )
        
        # Create website verification
        website_verifier = WebsiteVerifier()
        website_verification = website_verifier.create_verification(
            instance, 'institution', instance.official_website
        )
        
        # Log activity
        VerificationActivity.objects.create(
            content_object=instance,
            action='created',
            description='Institution verification request created',
            performer=request.user,
            new_status='draft'
        )
        
        return Response(
            InstitutionVerificationRequestSerializer(instance).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_document(self, request, pk=None):
        """Upload verification document"""
        instance = self.get_object()
        
        if instance.status not in ['draft', 'pending_documents']:
            return Response(
                {'error': 'Cannot upload documents in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file = request.FILES.get('file')
        document_type = request.data.get('document_type')
        
        if not file or not document_type:
            return Response(
                {'error': 'File and document_type are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate document
        doc_verifier = DocumentVerifier()
        is_valid, error_msg = doc_verifier.validate_file(file)
        
        if not is_valid:
            return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create document
        document = VerificationDocument.objects.create(
            content_object=instance,
            file=file,
            document_type=document_type,
            file_name=file.name,
            file_size=file.size,
            mime_type=file.content_type,
            file_hash=doc_verifier.calculate_file_hash(file)
        )
        
        # Log activity
        VerificationActivity.objects.create(
            content_object=instance,
            action='document_uploaded',
            description=f'Document uploaded: {document_type}',
            performer=request.user
        )
        
        return Response(
            VerificationDocumentSerializer(document, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def send_email_verification(self, request, pk=None):
        """Send email verification code"""
        instance = self.get_object()
        
        try:
            email_verification = EmailVerification.objects.get(
                content_type__model='institutionverificationrequest',
                object_id=instance.id
            )
        except EmailVerification.DoesNotExist:
            return Response(
                {'error': 'Email verification not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if email_verification.is_verified:
            return Response(
                {'message': 'Email already verified'},
                status=status.HTTP_200_OK
            )
        
        # Send verification email
        email_verifier = EmailVerifier()
        email_verifier.send_verification_email(email_verification)
        
        return Response(
            {'message': 'Verification code sent to email'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def verify_email(self, request, pk=None):
        """Verify email with code"""
        instance = self.get_object()
        serializer = EmailVerificationCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            email_verification = EmailVerification.objects.get(
                content_type__model='institutionverificationrequest',
                object_id=instance.id
            )
        except EmailVerification.DoesNotExist:
            return Response(
                {'error': 'Email verification not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        code = serializer.validated_data['verification_code']
        
        if email_verification.verification_code == code and not email_verification.is_expired():
            email_verification.is_verified = True
            email_verification.verified_at = timezone.now()
            email_verification.save()
            
            # Log activity
            VerificationActivity.objects.create(
                content_object=instance,
                action='email_verified',
                description='Official email verified',
                performer=request.user
            )
            
            return Response(
                {'message': 'Email verified successfully'},
                status=status.HTTP_200_OK
            )
        else:
            email_verification.attempts += 1
            email_verification.save()
            
            return Response(
                {'error': 'Invalid or expired verification code'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def verify_website(self, request, pk=None):
        """Verify website ownership"""
        instance = self.get_object()
        serializer = WebsiteVerificationCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            website_verification = WebsiteVerification.objects.get(
                content_type__model='institutionverificationrequest',
                object_id=instance.id
            )
        except WebsiteVerification.DoesNotExist:
            return Response(
                {'error': 'Website verification not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        method = serializer.validated_data['verification_method']
        website_verifier = WebsiteVerifier()
        
        # Perform verification based on method
        if method == 'dns':
            is_verified = website_verifier.verify_dns_record(website_verification)
        elif method == 'file':
            is_verified = website_verifier.verify_file_upload(website_verification)
        elif method == 'meta_tag':
            is_verified = website_verifier.verify_meta_tag(website_verification)
        else:
            return Response(
                {'error': 'Invalid verification method'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if is_verified:
            # Check SSL and security
            website_verifier.check_ssl(website_verification)
            website_verifier.check_google_safe_browsing(website_verification)
            
            # Log activity
            VerificationActivity.objects.create(
                content_object=instance,
                action='website_verified',
                description=f'Website verified using {method} method',
                performer=request.user
            )
            
            return Response(
                {'message': 'Website verified successfully'},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'error': 'Website verification failed'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit verification request for review"""
        instance = self.get_object()
        
        workflow = VerificationWorkflow()
        can_submit, error_msg = workflow.can_submit(instance, 'institution')
        
        if can_submit:
            instance.status = 'pending_review'
            instance.submission_date = timezone.now()
            instance.save()
            
            # Log activity
            VerificationActivity.objects.create(
                content_object=instance,
                action='submitted',
                description='Request submitted for review',
                performer=request.user,
                old_status='draft',
                new_status='pending_review'
            )
            
            return Response(
                {'message': 'Request submitted successfully'},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'error': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        """Approve verification request (admin only)"""
        instance = self.get_object()
        
        if instance.status != 'pending_review':
            return Response(
                {'error': 'Request is not pending review'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        instance.status = 'approved'
        instance.review_date = timezone.now()
        instance.activation_date = timezone.now()
        instance.reviewer = request.user
        instance.reviewer_notes = request.data.get('notes', '')
        instance.save()
        
        # Auto-activate institution
        workflow = VerificationWorkflow()
        workflow.auto_activate_institution(instance)
        
        # Log activity
        VerificationActivity.objects.create(
            content_object=instance,
            action='approved',
            description='Request approved',
            performer=request.user,
            old_status='pending_review',
            new_status='approved'
        )
        
        return Response(
            {'message': 'Request approved and institution activated'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reject(self, request, pk=None):
        """Reject verification request (admin only)"""
        instance = self.get_object()
        
        if instance.status != 'pending_review':
            return Response(
                {'error': 'Request is not pending review'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = request.data.get('reason', '')
        if not reason:
            return Response(
                {'error': 'Rejection reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        instance.status = 'rejected'
        instance.review_date = timezone.now()
        instance.reviewer = request.user
        instance.rejection_reason = reason
        instance.reviewer_notes = request.data.get('notes', '')
        instance.save()
        
        # Log activity
        VerificationActivity.objects.create(
            content_object=instance,
            action='rejected',
            description=f'Request rejected: {reason}',
            performer=request.user,
            old_status='pending_review',
            new_status='rejected'
        )
        
        return Response(
            {'message': 'Request rejected'},
            status=status.HTTP_200_OK
        )


class OrganizationVerificationViewSet(viewsets.ModelViewSet):
    """ViewSet for organization verification requests"""
    queryset = OrganizationVerificationRequest.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return OrganizationVerificationRequestCreateSerializer
        return OrganizationVerificationRequestSerializer
    
    def get_queryset(self):
        """Users can only see their own requests unless they're staff"""
        if self.request.user.is_staff:
            return OrganizationVerificationRequest.objects.all()
        return OrganizationVerificationRequest.objects.filter(submitter=self.request.user)
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create a new organization verification request"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create the request
        instance = serializer.save(
            submitter=request.user,
            status='draft'
        )
        
        # Create email verification
        email_verifier = EmailVerifier()
        email_verification = email_verifier.create_verification(
            instance, 'organization', instance.official_email
        )
        
        # Create website verification
        website_verifier = WebsiteVerifier()
        website_verification = website_verifier.create_verification(
            instance, 'organization', instance.official_website
        )
        
        # Log activity
        VerificationActivity.objects.create(
            content_object=instance,
            action='created',
            description='Organization verification request created',
            performer=request.user,
            new_status='draft'
        )
        
        return Response(
            OrganizationVerificationRequestSerializer(instance).data,
            status=status.HTTP_201_CREATED
        )
    
    # Same actions as InstitutionVerificationViewSet
    upload_document = InstitutionVerificationViewSet.upload_document
    send_email_verification = InstitutionVerificationViewSet.send_email_verification
    verify_email = InstitutionVerificationViewSet.verify_email
    verify_website = InstitutionVerificationViewSet.verify_website
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit verification request for review"""
        instance = self.get_object()
        
        workflow = VerificationWorkflow()
        can_submit, error_msg = workflow.can_submit(instance, 'organization')
        
        if can_submit:
            instance.status = 'pending_review'
            instance.submission_date = timezone.now()
            instance.save()
            
            # Log activity
            VerificationActivity.objects.create(
                content_object=instance,
                action='submitted',
                description='Request submitted for review',
                performer=request.user,
                old_status='draft',
                new_status='pending_review'
            )
            
            return Response(
                {'message': 'Request submitted successfully'},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'error': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        """Approve verification request (admin only)"""
        instance = self.get_object()
        
        if instance.status != 'pending_review':
            return Response(
                {'error': 'Request is not pending review'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        instance.status = 'approved'
        instance.review_date = timezone.now()
        instance.activation_date = timezone.now()
        instance.reviewer = request.user
        instance.reviewer_notes = request.data.get('notes', '')
        instance.save()
        
        # Auto-activate organization
        workflow = VerificationWorkflow()
        workflow.auto_activate_organization(instance)
        
        # Log activity
        VerificationActivity.objects.create(
            content_object=instance,
            action='approved',
            description='Request approved',
            performer=request.user,
            old_status='pending_review',
            new_status='approved'
        )
        
        return Response(
            {'message': 'Request approved and organization activated'},
            status=status.HTTP_200_OK
        )
    
    reject = InstitutionVerificationViewSet.reject
