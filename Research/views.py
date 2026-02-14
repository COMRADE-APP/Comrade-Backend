from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import (
    ResearchProject, ParticipantRequirements, ParticipantPosition,
    ResearchParticipant, ResearchGuidelines, PeerReview,
    ResearchPublication, ResearchMilestone
)
from .serializers import (
    ResearchProjectSerializer, ResearchProjectDetailSerializer,
    ParticipantRequirementsSerializer, ParticipantPositionSerializer,
    ResearchParticipantSerializer, ResearchGuidelinesSerializer,
    PeerReviewSerializer, ResearchPublicationSerializer,
    ResearchMilestoneSerializer
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
        return Response({'status': 'period_review'})

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
