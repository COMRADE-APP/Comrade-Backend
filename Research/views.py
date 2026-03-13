from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count
from datetime import datetime
from .models import (
    ResearchProject, ParticipantRequirements, ParticipantPosition,
    ResearchParticipant, ResearchGuidelines,
    PeerReview, ResearchPublication, ResearchMilestone,
    ParticipantApplication, ResearchAnalytics, RecruitmentPost,
    ResearcherApplication
)
from .serializers import (
    ResearchProjectSerializer, ResearchProjectDetailSerializer,
    ParticipantRequirementsSerializer, ParticipantPositionSerializer,
    ResearchParticipantSerializer, ResearchGuidelinesSerializer,
    PeerReviewSerializer, ResearchPublicationSerializer,
    ResearchMilestoneSerializer,
    ParticipantApplicationSerializer, ParticipantApplicationReviewSerializer,
    ResearchAnalyticsSerializer, RecruitmentPostSerializer,
    ResearcherApplicationSerializer
)

class IsPrincipalInvestigatorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.principal_investigator == request.user

class ResearchProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ResearchProjectSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'keywords']
    ordering_fields = ['created_at', 'views', 'start_date']

    def get_queryset(self):
        queryset = ResearchProject.objects.all()
        status_param = self.request.query_params.get('status')
        user_id = self.request.query_params.get('user_id')

        if status_param:
            queryset = queryset.filter(status=status_param)
        
        if user_id:
            queryset = queryset.filter(principal_investigator_id=user_id)
            
        return queryset

    def get_serializer_class(self):
        if self.action in ['retrieve', 'update', 'partial_update']:
            return ResearchProjectDetailSerializer
        return ResearchProjectSerializer

    def perform_create(self, serializer):
        if not getattr(self.request.user, 'is_researcher', False) and not self.request.user.is_staff:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only verified researchers can create research projects.")
        serializer.save(principal_investigator=self.request.user)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        project = self.get_object()
        if project.principal_investigator != request.user:
            return Response({'detail': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        project.status = 'published'
        project.is_published = True
        project.save()
        return Response({'status': 'published'})

    @action(detail=True, methods=['post'])
    def request_review(self, request, pk=None):
        project = self.get_object()
        if project.principal_investigator != request.user:
            return Response({'detail': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        project.status = 'peer_review'
        project.save()
        return Response({'status': 'peer_review'})

    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        """Apply to a research project position"""
        project = self.get_object()
        position_id = request.data.get('position_id')
        
        if not position_id:
            return Response({'detail': 'Position ID required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            position = ParticipantPosition.objects.get(id=position_id, research=project)
        except ParticipantPosition.DoesNotExist:
            return Response({'detail': 'Position not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if position.is_full:
            return Response({'detail': 'Position is full'}, status=status.HTTP_400_BAD_REQUEST)
        
        if ParticipantApplication.objects.filter(position=position, applicant=request.user).exists():
            return Response({'detail': 'Already applied'}, status=status.HTTP_400_BAD_REQUEST)
        
        application = ParticipantApplication.objects.create(
            position=position,
            applicant=request.user,
            cover_letter=request.data.get('cover_letter', ''),
            relevant_experience=request.data.get('relevant_experience', ''),
            availability=request.data.get('availability', ''),
        )
        
        ResearchAnalytics.objects.create(research=project, user=request.user, action='apply')
        return Response(ParticipantApplicationSerializer(application).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def applications(self, request, pk=None):
        """Get applications for a research project (PI only)"""
        project = self.get_object()
        if project.principal_investigator != request.user and not request.user.is_staff:
            return Response({'detail': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        apps = ParticipantApplication.objects.filter(position__research=project)
        status_filter = request.query_params.get('status')
        if status_filter:
            apps = apps.filter(status=status_filter)
        
        serializer = ParticipantApplicationSerializer(apps, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def record_view(self, request, pk=None):
        """Record a project view"""
        project = self.get_object()
        project.views += 1
        project.save(update_fields=['views'])
        user = request.user if request.user.is_authenticated else None
        ResearchAnalytics.objects.create(research=project, user=user, action='view')
        return Response({'status': 'recorded'})

    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get project analytics (PI only)"""
        project = self.get_object()
        if project.principal_investigator != request.user and not request.user.is_staff:
            return Response({'detail': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        from django.db.models.functions import TruncDate
        
        action_counts = dict(
            ResearchAnalytics.objects.filter(research=project)
            .values_list('action').annotate(count=Count('id'))
            .values_list('action', 'count')
        )
        
        daily_views = list(
            ResearchAnalytics.objects.filter(research=project, action='view')
            .annotate(date=TruncDate('created_at'))
            .values('date').annotate(count=Count('id'))
            .order_by('date').values('date', 'count')[:30]
        )
        
        return Response({
            'views': project.views,
            'action_counts': action_counts,
            'daily_views': daily_views,
            'total_applications': ParticipantApplication.objects.filter(position__research=project).count(),
            'accepted_applications': ParticipantApplication.objects.filter(position__research=project, status='accepted').count(),
            'total_participants': ResearchParticipant.objects.filter(research=project).count(),
            'positions_count': project.positions.count(),
        })

class ParticipantPositionViewSet(viewsets.ModelViewSet):
    serializer_class = ParticipantPositionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return ParticipantPosition.objects.all()

    def perform_create(self, serializer):
        # Ensure only PI can create positions
        research_id = self.request.data.get('research')
        if research_id:
            research = ResearchProject.objects.get(id=research_id)
            if research.principal_investigator != self.request.user:
                raise permissions.PermissionDenied("Only the Principal Investigator can create positions.")
        serializer.save()

class ResearchParticipantViewSet(viewsets.ModelViewSet):
    serializer_class = ResearchParticipantSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Return projects user is participating in
        return ResearchParticipant.objects.filter(user=user)

    @action(detail=False, methods=['post'])
    def join(self, request):
        position_id = request.data.get('position_id')
        research_id = request.data.get('research_id')
        
        if not position_id or not research_id:
            return Response({'detail': 'Position ID and Research ID required'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Check if already joined
        if ResearchParticipant.objects.filter(user=request.user, research_id=research_id).exists():
             return Response({'detail': 'Already a participant'}, status=status.HTTP_400_BAD_REQUEST)

        participant = ResearchParticipant.objects.create(
            user=request.user,
            research_id=research_id,
            position_id=position_id,
            status='active' # Or 'invited' depending on logic
        )
        return Response(ResearchParticipantSerializer(participant).data)

class PeerReviewViewSet(viewsets.ModelViewSet):
    serializer_class = PeerReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PeerReview.objects.filter(reviewer=self.request.user)


class ResearchPublicationViewSet(viewsets.ModelViewSet):
    serializer_class = ResearchPublicationSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return ResearchPublication.objects.all()

    def perform_create(self, serializer):
        research_id = self.request.data.get('research')
        if research_id:
            research = ResearchProject.objects.get(id=research_id)
            if research.principal_investigator != self.request.user:
                raise permissions.PermissionDenied("Only the Principal Investigator can publish.")
        serializer.save()

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.research.principal_investigator != self.request.user:
            raise permissions.PermissionDenied("Only the Principal Investigator can edit the publication.")
        serializer.save()


class ParticipantApplicationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing participant applications"""
    serializer_class = ParticipantApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return ParticipantApplication.objects.filter(applicant=user)

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """Review an application (PI only)"""
        application = self.get_object()
        research = application.position.research
        
        if research.principal_investigator != request.user and not request.user.is_staff:
            return Response({'detail': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ParticipantApplicationReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        application.status = serializer.validated_data['status']
        application.reviewer_notes = serializer.validated_data.get('reviewer_notes', '')
        application.reviewed_by = request.user
        application.reviewed_at = datetime.now()
        application.save()
        
        # If accepted, create participant record and update slot count
        if application.status == 'accepted':
            ResearchParticipant.objects.get_or_create(
                research=research,
                user=application.applicant,
                defaults={'position': application.position, 'status': 'accepted'}
            )
            position = application.position
            position.slots_filled += 1
            position.save(update_fields=['slots_filled'])
        
        return Response(ParticipantApplicationSerializer(application, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        """Withdraw own application"""
        application = self.get_object()
        if application.applicant != request.user:
            return Response({'detail': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        if application.status in ['accepted', 'rejected']:
            return Response({'detail': 'Cannot withdraw at this stage'}, status=status.HTTP_400_BAD_REQUEST)
        
        application.status = 'withdrawn'
        application.save()
        return Response(ParticipantApplicationSerializer(application, context={'request': request}).data)

    @action(detail=False, methods=['get'])
    def my_applications(self, request):
        """Get current user's applications across all research"""
        apps = ParticipantApplication.objects.filter(applicant=request.user)
        serializer = ParticipantApplicationSerializer(apps, many=True, context={'request': request})
        return Response(serializer.data)


class RecruitmentPostViewSet(viewsets.ModelViewSet):
    """ViewSet for managing recruitment posts"""
    serializer_class = RecruitmentPostSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'apply']:
            return [permissions.IsAuthenticatedOrReadOnly()]
        return [permissions.IsAuthenticated(), IsPrincipalInvestigatorOrReadOnly()]
        
    def get_queryset(self):
        queryset = RecruitmentPost.objects.all()
        research_id = self.request.query_params.get('research', None)
        if research_id:
            queryset = queryset.filter(research_id=research_id)
            
        # non-PI users only see active posts
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_active=True)
        else:
            # Need a more robust check if we wanted, but for now just filter out inactive ones for non-staff/non-owners
            pass
            
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def apply(self, request, pk=None):
        """Submit multi-step application to a recruitment post"""
        post = self.get_object()
        position_id = request.data.get('position_id')
        
        if not position_id:
            return Response({'error': 'position_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            position = post.positions.get(id=position_id)
        except ParticipantPosition.DoesNotExist:
            return Response({'error': 'Invalid position_id for this post'}, status=status.HTTP_404_NOT_FOUND)
            
        if position.is_full:
            return Response({'error': 'This position is already full.'}, status=status.HTTP_400_BAD_REQUEST)
            
        if ParticipantApplication.objects.filter(position=position, applicant=request.user).exists():
            return Response({'error': 'You have already applied for this position.'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Create application including form_data
        application = ParticipantApplication.objects.create(
            position=position,
            applicant=request.user,
            cover_letter=request.data.get('cover_letter', ''),
            relevant_experience=request.data.get('relevant_experience', ''),
            availability=request.data.get('availability', ''),
            form_data=request.data.get('form_data', {})
        )
        
        # Track analytics
        ResearchAnalytics.objects.create(research=post.research, user=request.user, action='apply')
        
        serializer = ParticipantApplicationSerializer(application, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def applications(self, request, pk=None):
        """Get all applications for this recruitment post's positions (PI only)"""
        post = self.get_object()
        if post.research.principal_investigator != request.user and not request.user.is_staff:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
            
        positions = post.positions.all()
        applications = ParticipantApplication.objects.filter(position__in=positions).order_by('-applied_at')
        
        serializer = ParticipantApplicationSerializer(applications, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def convert_to_opinion(self, request, pk=None):
        """Convert recruitment post to an opinion/announcement (Stub for now)"""
        post = self.get_object()
        if not post.can_convert_to_opinion:
            return Response({'error': 'Cannot convert to opinion'}, status=status.HTTP_400_BAD_REQUEST)
        
        if post.research.principal_investigator != request.user and not request.user.is_staff:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
            
        # Logic to create corresponding GeneralOpinion or announcement
        return Response({'message': 'Post converted successfully (stub)'}, status=status.HTTP_200_OK)

class ResearcherApplicationViewSet(viewsets.ModelViewSet):
    """ViewSet for users applying to become verified researchers"""
    serializer_class = ResearcherApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return ResearcherApplication.objects.all()
        return ResearcherApplication.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        from rest_framework.exceptions import ValidationError
        # Prevent multiple pending applications
        if ResearcherApplication.objects.filter(user=self.request.user, status='pending').exists():
            raise ValidationError({"detail": "You already have a pending application."})
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def review(self, request, pk=None):
        """Admin review of application"""
        application = self.get_object()
        status_update = request.data.get('status')
        if status_update not in ['approved', 'rejected']:
            return Response({'error': 'Invalid status. Use "approved" or "rejected".'}, status=status.HTTP_400_BAD_REQUEST)
        
        application.status = status_update
        application.reviewer_notes = request.data.get('reviewer_notes', '')
        application.reviewed_at = datetime.now()
        application.save()
        
        if status_update == 'approved':
            user = application.user
            user.is_researcher = True
            user.save(update_fields=['is_researcher'])
            
        return Response(ResearcherApplicationSerializer(application).data)

