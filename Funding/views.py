from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from .models import (
    Business, FundingDocument, FundingRequest, InvestmentOpportunity,
    FundingResponse, FundingNegotiation, NegotiationMessage, FundingReaction,
    CapitalVenture, VentureBid
)
from .serializers import (
    BusinessSerializer, BusinessCreateSerializer, 
    FundingDocumentSerializer, FundingRequestSerializer,
    InvestmentOpportunitySerializer, FundingResponseSerializer,
    FundingNegotiationSerializer, NegotiationMessageSerializer,
    FundingReactionSerializer, CapitalVentureSerializer, VentureBidSerializer
)

class IsFounderOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    Assumes the model instance has an `founder` attribute.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.founder == request.user

class BusinessViewSet(viewsets.ModelViewSet):
    queryset = Business.objects.all().order_by('-created_at')
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsFounderOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'industry', 'description']
    filterset_fields = ['industry', 'stage']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return BusinessCreateSerializer
        return BusinessSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # Filter by charity status
        is_charity = self.request.query_params.get('is_charity')
        if is_charity is not None:
            qs = qs.filter(is_charity=is_charity.lower() == 'true')
        return qs

    def perform_create(self, serializer):
        serializer.save(founder=self.request.user)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_businesses(self, request):
        businesses = Business.objects.filter(founder=request.user)
        serializer = BusinessSerializer(businesses, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def charities(self, request):
        """List only charity businesses"""
        charities = Business.objects.filter(is_charity=True)
        serializer = BusinessSerializer(charities, many=True)
        return Response(serializer.data)

class FundingDocumentViewSet(viewsets.ModelViewSet):
    queryset = FundingDocument.objects.all()
    serializer_class = FundingDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Allow filtering by business
        business_id = self.request.query_params.get('business_id')
        qs = self.queryset
        if business_id:
            qs = qs.filter(business_id=business_id)
        # Only return viewable documents to non-owners
        if not self.request.user.is_staff:
            qs = qs.filter(is_viewable=True) | qs.filter(business__founder=self.request.user)
        return qs.distinct()

    def perform_create(self, serializer):
        # Verify user owns the business
        business = serializer.validated_data['business']
        if business.founder != self.request.user:
            raise permissions.PermissionDenied("You can only upload documents for your own business.")
        document = serializer.save()
        
        # Trigger async scan (run synchronously in dev, use Celery in production)
        try:
            from Funding.services.file_scanner import process_document_scan
            process_document_scan(str(document.id))
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Scan trigger failed: {e}")


class FundingRequestViewSet(viewsets.ModelViewSet):
    queryset = FundingRequest.objects.all()
    serializer_class = FundingRequestSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        business = serializer.validated_data['business']
        if business.founder != self.request.user:
            raise permissions.PermissionDenied("You can only request funding for your own business.")
        serializer.save()

class InvestmentOpportunityViewSet(viewsets.ModelViewSet):
    """
    Read-only for normal users, write for Admins
    """
    queryset = InvestmentOpportunity.objects.filter(is_active=True)
    serializer_class = InvestmentOpportunitySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'provider', 'type']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticatedOrReadOnly()]


# ==============================================================================
# FUNDING RESPONSES & INTERACTIONS
# ==============================================================================

class FundingResponseViewSet(viewsets.ModelViewSet):
    """Comments, questions, and offers on funding requests"""
    queryset = FundingResponse.objects.all()
    serializer_class = FundingResponseSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        funding_request_id = self.request.query_params.get('funding_request_id')
        if funding_request_id:
            qs = qs.filter(funding_request_id=funding_request_id)
        response_type = self.request.query_params.get('response_type')
        if response_type:
            qs = qs.filter(response_type=response_type)
        return qs

    def perform_create(self, serializer):
        serializer.save(responder=self.request.user)


class FundingNegotiationViewSet(viewsets.ModelViewSet):
    """Private negotiation threads between founders and investors"""
    queryset = FundingNegotiation.objects.all()
    serializer_class = FundingNegotiationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Users can only see their own negotiations
        user = self.request.user
        return self.queryset.filter(Q(investor=user) | Q(founder=user))

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send a message in a negotiation"""
        negotiation = self.get_object()
        content = request.data.get('content')
        if not content:
            return Response({'error': 'Content required'}, status=status.HTTP_400_BAD_REQUEST)
        
        message = NegotiationMessage.objects.create(
            negotiation=negotiation,
            sender=request.user,
            content=content,
            attachment=request.data.get('attachment')
        )
        serializer = NegotiationMessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FundingReactionViewSet(viewsets.ModelViewSet):
    """Reactions to funding requests"""
    queryset = FundingReaction.objects.all()
    serializer_class = FundingReactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        funding_request_id = self.request.query_params.get('funding_request_id')
        if funding_request_id:
            qs = qs.filter(funding_request_id=funding_request_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'])
    def toggle(self, request):
        """Toggle a reaction on a funding request"""
        funding_request_id = request.data.get('funding_request_id')
        reaction_type = request.data.get('reaction_type')
        
        if not funding_request_id or not reaction_type:
            return Response({'error': 'funding_request_id and reaction_type required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        existing = FundingReaction.objects.filter(
            funding_request_id=funding_request_id,
            user=request.user
        ).first()
        
        if existing:
            if existing.reaction_type == reaction_type:
                existing.delete()
                return Response({'status': 'removed'})
            else:
                existing.reaction_type = reaction_type
                existing.save()
                return Response({'status': 'updated', 'reaction': reaction_type})
        else:
            FundingReaction.objects.create(
                funding_request_id=funding_request_id,
                user=request.user,
                reaction_type=reaction_type
            )
            return Response({'status': 'added', 'reaction': reaction_type})


# ==============================================================================
# CAPITAL VENTURES
# ==============================================================================

class CapitalVentureViewSet(viewsets.ModelViewSet):
    """Investment funds managed by organizations"""
    queryset = CapitalVenture.objects.filter(is_active=True)
    serializer_class = CapitalVentureSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description', 'investment_criteria']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticatedOrReadOnly()]


class VentureBidViewSet(viewsets.ModelViewSet):
    """Bids from capital ventures on funding requests"""
    queryset = VentureBid.objects.all()
    serializer_class = VentureBidSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'proposed_amount']

    def get_queryset(self):
        qs = super().get_queryset()
        funding_request_id = self.request.query_params.get('funding_request_id')
        if funding_request_id:
            qs = qs.filter(funding_request_id=funding_request_id)
        venture_id = self.request.query_params.get('venture_id')
        if venture_id:
            qs = qs.filter(venture_id=venture_id)
        return qs

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update bid status (for founders to accept/reject)"""
        bid = self.get_object()
        new_status = request.data.get('status')
        
        # Verify user is founder of the business
        if bid.funding_request.business.founder != request.user:
            return Response({'error': 'Only the business founder can update bid status'},
                          status=status.HTTP_403_FORBIDDEN)
        
        if new_status not in ['accepted', 'rejected', 'negotiating']:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
        bid.status = new_status
        bid.save()
        serializer = VentureBidSerializer(bid)
        return Response(serializer.data)

