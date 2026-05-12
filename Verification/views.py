"""
Verification Views for all entity types including liveness detection
"""
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime, timedelta
import secrets
import hashlib

from .models import (
    EntityVerificationRequest, EntityBasicInfo, EntityLocation,
    EntityContact, EntityRegistration, EntityTaxInfo,
    EntityIdentification, VerificationDocument, VerificationActivity,
    LivenessVerification, VerificationVideo, VerificationChecklist
)
from .serializers import (
    EntityVerificationRequestSerializer, EntityVerificationRequestCreateSerializer,
    EntityVerificationRequestUpdateSerializer, StaffVerificationReviewSerializer,
    VerificationDocumentSerializer, EntityIdentificationSerializer,
    LivenessVerificationSerializer, LivenessInitiationSerializer,
    LivenessCompletionSerializer, VerificationVideoSerializer,
    VerificationChecklistSerializer, BulkVerificationActionSerializer
)


class EntityVerificationViewSet(viewsets.ModelViewSet):
    """ViewSet for entity verification requests"""
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    
    def get_permissions(self):
        if self.action in ['create', 'initiate_liveness', 'complete_liveness']:
            return [AllowAny()]
        elif self.action in ['staff_dashboard', 'bulk_action']:
            return [IsAuthenticated()]
        return [IsAuthenticated()]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return EntityVerificationRequestCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return EntityVerificationRequestUpdateSerializer
        elif self.action == 'staff_dashboard':
            return StaffVerificationReviewSerializer
        return EntityVerificationRequestSerializer
    
    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return EntityVerificationRequest.objects.none()
        
        if hasattr(user, 'is_staff') and user.is_staff:
            return EntityVerificationRequest.objects.all()
        
        return EntityVerificationRequest.objects.filter(submitted_by=user)
    
    def create(self, request, *args, **kwargs):
        serializer = EntityVerificationRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user if request.user.is_authenticated else None
        
        verification_request = EntityVerificationRequest.objects.create(
            entity_type=serializer.validated_data['entity_type'],
            verification_type=serializer.validated_data['entity_type'],
            submitted_by=user,
            status='draft'
        )
        
        EntityBasicInfo.objects.create(
            verification_request=verification_request,
            name=serializer.validated_data['name'],
            description=serializer.validated_data.get('description', '')
        )
        
        EntityLocation.objects.create(
            verification_request=verification_request,
            country=serializer.validated_data['country'],
            state=serializer.validated_data.get('state', ''),
            city=serializer.validated_data['city'],
            address=serializer.validated_data['address'],
            postal_code=serializer.validated_data.get('postal_code', ''),
            is_virtual=serializer.validated_data.get('is_virtual', False),
            virtual_link=serializer.validated_data.get('virtual_link', '')
        )
        
        EntityContact.objects.create(
            verification_request=verification_request,
            email=serializer.validated_data['email'],
            phone_number=serializer.validated_data['phone_number'],
            website=serializer.validated_data.get('website', ''),
            social_media=serializer.validated_data.get('social_media', {})
        )
        
        EntityRegistration.objects.create(
            verification_request=verification_request,
            registration_number=serializer.validated_data['registration_number'],
            year_established=serializer.validated_data.get('year_established'),
            legal_name=serializer.validated_data.get('legal_name', ''),
            jurisdiction=serializer.validated_data.get('jurisdiction', '')
        )
        
        tax_data = serializer.validated_data
        if tax_data.get('has_tax_id') or tax_data.get('tax_id'):
            EntityTaxInfo.objects.create(
                verification_request=verification_request,
                has_tax_id=tax_data.get('has_tax_id', False),
                tax_id=tax_data.get('tax_id', ''),
                tax_system=tax_data.get('tax_system', ''),
                tax_jurisdiction=tax_data.get('tax_jurisdiction', ''),
                vat_number=tax_data.get('vat_number', ''),
                GST_number=tax_data.get('GST_number', '')
            )
        
        identifications = serializer.validated_data.get('identifications', [])
        for id_data in identifications:
            EntityIdentification.objects.create(
                verification_request=verification_request,
                identification_type=id_data.get('type', 'other'),
                document_number=id_data.get('number', ''),
                document_file=id_data.get('file'),
                issuing_country=id_data.get('issuing_country', ''),
                issuing_authority=id_data.get('issuing_authority', '')
            )
        
        for item in ['registration_doc', 'tax_doc', 'address_proof', 'id_document', 'liveness_video']:
            VerificationChecklist.objects.create(
                verification_request=verification_request,
                item=item,
                is_required=True
            )
        
        VerificationActivity.objects.create(
            verification_request=verification_request,
            action='created',
            performed_by=user,
            details={'entity_type': verification_request.entity_type}
        )
        
        return Response(
            EntityVerificationRequestSerializer(verification_request).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['post'])
    def submit(self, request):
        verification_id = request.data.get('verification_id')
        verification_request = get_object_or_404(
            EntityVerificationRequest,
            id=verification_id,
            submitted_by=request.user
        )
        
        if verification_request.status != 'draft':
            return Response(
                {'error': 'Only draft applications can be submitted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        verification_request.status = 'submitted'
        verification_request.submitted_at = timezone.now()
        verification_request.save()
        
        VerificationActivity.objects.create(
            verification_request=verification_request,
            action='submitted',
            performed_by=request.user,
            details={'status': 'submitted'}
        )
        
        return Response({'status': 'submitted', 'verification_id': str(verification_request.id)})
    
    @action(detail=False, methods=['get'])
    def staff_dashboard(self, request):
        status_filter = request.query_params.get('status')
        entity_type = request.query_params.get('entity_type')
        
        queryset = EntityVerificationRequest.objects.all()
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = StaffVerificationReviewSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = StaffVerificationReviewSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        serializer = BulkVerificationActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        verification_ids = serializer.validated_data['verification_ids']
        action = serializer.validated_data['action']
        notes = serializer.validated_data.get('notes', '')
        
        updated_count = 0
        for vid in verification_ids:
            verification = get_object_or_404(EntityVerificationRequest, id=vid)
            
            if action == 'approve':
                verification.status = 'approved'
                verification.is_verified = True
                verification.verified_at = timezone.now()
                verification.reviewer = request.user
                verification.reviewed_at = timezone.now()
                verification.verification_badge = f"verified_{verification.entity_type}"
                verification.save()
                
                VerificationActivity.objects.create(
                    verification_request=verification,
                    action='approved',
                    performed_by=request.user,
                    details={'notes': notes}
                )
            
            elif action == 'reject':
                verification.status = 'rejected'
                verification.rejection_reason = notes
                verification.reviewer = request.user
                verification.reviewed_at = timezone.now()
                verification.save()
                
                VerificationActivity.objects.create(
                    verification_request=verification,
                    action='rejected',
                    performed_by=request.user,
                    details={'reason': notes}
                )
            
            elif action == 'request_info':
                verification.status = 'additional_info'
                verification.additional_info_request = notes
                verification.save()
                
                VerificationActivity.objects.create(
                    verification_request=verification,
                    action='info_requested',
                    performed_by=request.user,
                    details={'message': notes}
                )
            
            updated_count += 1
        
        return Response({'updated': updated_count})


class LivenessVerificationViewSet(viewsets.ModelViewSet):
    """ViewSet for liveness verification"""
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    
    def get_permissions(self):
        if self.action in ['initiate', 'get_session']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def get_serializer_class(self):
        if self.action == 'initiate':
            return LivenessInitiationSerializer
        elif self.action == 'complete':
            return LivenessCompletionSerializer
        return LivenessVerificationSerializer
    
    def get_queryset(self):
        return LivenessVerification.objects.all()
    
    @action(detail=False, methods=['post'])
    def initiate(self, request):
        verification_id = request.data.get('verification_request_id')
        
        verification_request = get_object_or_404(
            EntityVerificationRequest,
            id=verification_id
        )
        
        liveness = LivenessVerification.objects.create(
            verification_request=verification_request,
            status='pending',
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        verification_request.status = 'pending_liveness'
        verification_request.save()
        
        VerificationActivity.objects.create(
            verification_request=verification_request,
            action='liveness_initiated',
            details={'session_id': liveness.session_id}
        )
        
        return Response({
            'session_id': liveness.session_id,
            'verification_token': liveness.verification_token,
            'expires_at': liveness.expires_at,
            'instructions': {
                'challenge_type': 'random_movement',
                'duration_seconds': 30,
                'requirements': [
                    'Ensure good lighting',
                    'Face the camera directly',
                    'Remove glasses and hat',
                    'No other persons in frame',
                    'Complete the random movements shown on screen'
                ]
            }
        })
    
    @action(detail=False, methods=['get'])
    def get_session(self, request):
        session_id = request.query_params.get('session_id')
        liveness = get_object_or_404(LivenessVerification, session_id=session_id)
        
        return Response({
            'status': liveness.status,
            'expires_at': liveness.expires_at
        })
    
    @action(detail=False, methods=['post'])
    def complete(self, request):
        session_id = request.data.get('session_id')
        
        liveness = get_object_or_404(LivenessVerification, session_id=session_id)
        
        if liveness.is_expired():
            liveness.status = 'expired'
            liveness.save()
            return Response(
                {'error': 'Session expired'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        liveness.status = 'completed'
        liveness.completed_at = timezone.now()
        
        liveness.face_detected = request.data.get('face_detected', False)
        liveness.multiple_faces = request.data.get('multiple_faces', False)
        liveness.screen_recording_detected = request.data.get('screen_recording_detected', False)
        liveness.mask_detected = request.data.get('mask_detected', False)
        liveness.liveness_score = request.data.get('liveness_score', 0)
        
        liveness.liveness_verified = (
            liveness.face_detected and 
            not liveness.multiple_faces and 
            not liveness.screen_recording_detected and
            not liveness.mask_detected and
            liveness.liveness_score >= 0.7
        )
        
        if request.FILES.get('video'):
            liveness.video_file = request.FILES['video']
        
        liveness.save()
        
        verification_request = liveness.verification_request
        if liveness.liveness_verified:
            verification_request.status = 'under_review'
            verification_request.save()
            
            VerificationActivity.objects.create(
                verification_request=verification_request,
                action='liveness_completed',
                details={
                    'liveness_verified': True,
                    'liveness_score': liveness.liveness_score
                }
            )
        else:
            verification_request.status = 'liveness_failed'
            verification_request.save()
            
            VerificationActivity.objects.create(
                verification_request=verification_request,
                action='liveness_failed',
                details={
                    'liveness_verified': False,
                    'reason': 'Liveness check failed'
                }
            )
        
        return Response({
            'liveness_verified': liveness.liveness_verified,
            'liveness_score': liveness.liveness_score,
            'status': verification_request.status
        })
    
    @action(detail=False, methods=['post'])
    def retry(self, request):
        verification_id = request.data.get('verification_request_id')
        verification_request = get_object_or_404(
            EntityVerificationRequest,
            id=verification_id
        )
        
        if verification_request.status != 'liveness_failed':
            return Response(
                {'error': 'Can only retry after failed liveness'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return self.initiate(request)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class VerificationDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for verification documents"""
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        return VerificationDocumentSerializer
    
    def get_queryset(self):
        user = self.request.user
        verification_id = self.request.query_params.get('verification_request_id')
        
        if hasattr(user, 'is_staff') and user.is_staff:
            if verification_id:
                return VerificationDocument.objects.filter(object_id=verification_id)
            return VerificationDocument.objects.all()
        
        return VerificationDocument.objects.filter(
            object_id__in=EntityVerificationRequest.objects.filter(submitted_by=user).values_list('id', flat=True)
        )
    
    def perform_create(self, serializer):
        verification_id = self.request.data.get('verification_request_id')
        verification_request = get_object_or_404(
            EntityVerificationRequest,
            id=verification_id,
            submitted_by=self.request.user
        )
        
        document = serializer.save(
            content_type=ContentType.objects.get_for_model(EntityVerificationRequest),
            object_id=verification_request.id,
            verification_request=verification_request
        )
        
        VerificationActivity.objects.create(
            verification_request=verification_request,
            action='document_uploaded',
            performed_by=self.request.user,
            details={'document_type': document.document_type, 'document_name': document.document_name}
        )
        
        checklist_item = VerificationChecklist.objects.filter(
            verification_request=verification_request,
            item=self.request.data.get('document_type', 'other')
        ).first()
        
        if checklist_item:
            checklist_item.is_completed = True
            checklist_item.completed_at = timezone.now()
            checklist_item.document = document
            checklist_item.save()


class VerificationVideoViewSet(viewsets.ModelViewSet):
    """ViewSet for verification videos"""
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        return VerificationVideoSerializer
    
    def get_queryset(self):
        user = self.request.user
        verification_id = self.request.query_params.get('verification_request_id')
        
        if hasattr(user, 'is_staff') and user.is_staff:
            if verification_id:
                return VerificationVideo.objects.filter(verification_request_id=verification_id)
            return VerificationVideo.objects.all()
        
        return VerificationVideo.objects.filter(
            verification_request__submitted_by=user
        )
    
    def perform_create(self, serializer):
        verification_id = self.request.data.get('verification_request_id')
        verification_request = get_object_or_404(
            EntityVerificationRequest,
            id=verification_id,
            submitted_by=self.request.user
        )
        
        video = serializer.save(verification_request=verification_request)
        
        if video.video_type == 'liveness':
            checklist_item = VerificationChecklist.objects.filter(
                verification_request=verification_request,
                item='liveness_video'
            ).first()
            
            if checklist_item:
                checklist_item.is_completed = True
                checklist_item.completed_at = timezone.now()
                checklist_item.save()


class IdentificationVerificationViewSet(viewsets.ModelViewSet):
    """ViewSet for ID verification"""
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        return EntityIdentificationSerializer
    
    def get_queryset(self):
        user = self.request.user
        verification_id = self.request.query_params.get('verification_request_id')
        
        if hasattr(user, 'is_staff') and user.is_staff:
            if verification_id:
                return EntityIdentification.objects.filter(verification_request_id=verification_id)
            return EntityIdentification.objects.all()
        
        return EntityIdentification.objects.filter(
            verification_request__submitted_by=user
        )
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        identification = self.get_object()
        
        identification.is_verified = True
        identification.verified_by = request.user
        identification.verified_at = timezone.now()
        identification.verification_notes = request.data.get('notes', '')
        identification.save()
        
        VerificationActivity.objects.create(
            verification_request=identification.verification_request,
            action='document_verified',
            performed_by=request.user,
            details={
                'identification_type': identification.identification_type,
                'document_number': identification.document_number
            }
        )
        
        return Response({'status': 'verified'})


class VerificationChecklistViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for verification checklist"""
    serializer_class = VerificationChecklistSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        verification_id = self.request.query_params.get('verification_request_id')
        
        if not verification_id:
            return VerificationChecklist.objects.none()
        
        return VerificationChecklist.objects.filter(verification_request_id=verification_id)


class VerificationStatsView(generics.ListAPIView):
    """API endpoint for verification statistics"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        total = EntityVerificationRequest.objects.count()
        pending = EntityVerificationRequest.objects.filter(status='submitted').count()
        under_review = EntityVerificationRequest.objects.filter(status='under_review').count()
        approved = EntityVerificationRequest.objects.filter(status='approved').count()
        rejected = EntityVerificationRequest.objects.filter(status='rejected').count()
        activated = EntityVerificationRequest.objects.filter(status='activated').count()
        
        by_type = {}
        for entity_type, _ in EntityVerificationRequest.ENTITY_TYPES:
            by_type[entity_type] = EntityVerificationRequest.objects.filter(
                entity_type=entity_type
            ).count()
        
        return Response({
            'total': total,
            'pending': pending,
            'under_review': under_review,
            'approved': approved,
            'rejected': rejected,
            'activated': activated,
            'by_type': by_type
        })