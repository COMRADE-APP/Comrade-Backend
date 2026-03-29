from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    Business, FundingDocument, FundingRequest, InvestmentOpportunity,
    FundingResponse, FundingNegotiation, NegotiationMessage, FundingReaction,
    CapitalVenture, VentureBid, InvestmentAgreement, InvestorProfile
)
from .serializers import (
    BusinessSerializer, BusinessCreateSerializer, 
    FundingDocumentSerializer, FundingRequestSerializer,
    InvestmentOpportunitySerializer, FundingResponseSerializer,
    FundingNegotiationSerializer, NegotiationMessageSerializer,
    FundingReactionSerializer, CapitalVentureSerializer, VentureBidSerializer,
    InvestmentAgreementSerializer, InvestorProfileSerializer
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

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_requests(self, request):
        """Get funding requests for the current user's businesses"""
        requests = FundingRequest.objects.filter(
            business__founder=request.user
        ).select_related('business', 'target_venture').order_by('-created_at')
        serializer = FundingRequestSerializer(requests, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def get_or_create_negotiation(self, request, pk=None):
        """Get or create a negotiation thread for this funding request"""
        funding_request = self.get_object()
        
        # Determine roles based on who is requesting
        if request.user == funding_request.business.founder:
            # Founder is checking - they need to specify which investor
            investor_id = request.data.get('investor_id')
            if not investor_id:
                return Response({'error': 'investor_id required when founder initiates'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                investor = User.objects.get(id=investor_id)
            except User.DoesNotExist:
                return Response({'error': 'Investor not found'}, status=status.HTTP_404_NOT_FOUND)
            
            founder = request.user
        else:
            # Investor is initiating
            investor = request.user
            founder = funding_request.business.founder

        negotiation, created = FundingNegotiation.objects.get_or_create(
            funding_request=funding_request,
            investor=investor,
            founder=founder
        )
        
        serializer = FundingNegotiationSerializer(negotiation)
        return Response(serializer.data, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)

class InvestmentOpportunityViewSet(viewsets.ModelViewSet):
    """
    Read-only for normal users, write for Admins
    """
    queryset = InvestmentOpportunity.objects.filter(is_active=True)
    serializer_class = InvestmentOpportunitySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    search_fields = ['title', 'provider', 'type']
    filterset_fields = ['type', 'risk_level']

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

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Get all messages in a negotiation"""
        negotiation = self.get_object()
        messages = negotiation.messages.all().order_by('created_at')
        from .serializers import NegotiationMessageSerializer
        serializer = NegotiationMessageSerializer(messages, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send a message in a negotiation"""
        negotiation = self.get_object()
        content = request.data.get('content')
        if not content and not request.data.get('attachment'):
            return Response({'error': 'Content or attachment required'}, status=status.HTTP_400_BAD_REQUEST)
        
        from .models import NegotiationMessage
        message = NegotiationMessage.objects.create(
            negotiation=negotiation,
            sender=request.user,
            content=content or '',
            attachment=request.data.get('attachment')
        )
        from .serializers import NegotiationMessageSerializer
        serializer = NegotiationMessageSerializer(message, context={'request': request})
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
    search_fields = ['name', 'description', 'investment_criteria', 'investment_focus']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticatedOrReadOnly()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_ventures(self, request):
        """Get ventures the user is associated with"""
        ventures = CapitalVenture.objects.filter(
            Q(created_by=request.user) |
            Q(organisation__organisation_members__user=request.user) |
            Q(institution__members__user=request.user)
        ).distinct()
        serializer = CapitalVentureSerializer(ventures, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def add_funds(self, request, pk=None):
        """Add additional funds to the VC"""
        venture = self.get_object()
        
        # Verify user has permission to add funds
        if venture.created_by != request.user:
            return Response(
                {'error': 'You do not have permission to add funds to this venture'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        amount = request.data.get('amount')
        if not amount:
            return Response({'error': 'amount is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            return Response({'error': 'amount must be a positive number'}, status=status.HTTP_400_BAD_REQUEST)

        # Increment total and available funds
        venture.total_fund = float(venture.total_fund) + amount
        venture.available_fund = float(venture.available_fund) + amount
        venture.save()
        
        serializer = CapitalVentureSerializer(venture)
        return Response({
            'message': f'Successfully added KES {amount:,.2f} to the fund.',
            'venture': serializer.data
        })

    @action(detail=True, methods=['get'])
    def funding_requests(self, request, pk=None):
        """Get all funding requests targeted at this venture"""
        venture = self.get_object()
        requests = venture.received_requests.all().order_by('-created_at')
        serializer = FundingRequestSerializer(requests, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def review_request(self, request, pk=None):
        """Review and change status of a funding request"""
        venture = self.get_object()
        
        # Verify user has permission to review (creator or org member)
        if venture.created_by != request.user:
            # Check org/institution membership (simplified check)
            if venture.organisation and not hasattr(venture.organisation, 'members'):
                return Response(
                    {'error': 'You do not have permission to review requests for this venture'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        funding_request_id = request.data.get('funding_request_id')
        new_status = request.data.get('status')
        notes = request.data.get('notes', '')
        documents_requested = request.data.get('documents_requested', '')
        
        if not funding_request_id or not new_status:
            return Response(
                {'error': 'funding_request_id and status are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            funding_request = FundingRequest.objects.get(id=funding_request_id, target_venture=venture)
        except FundingRequest.DoesNotExist:
            return Response({'error': 'Funding request not found'}, status=status.HTTP_404_NOT_FOUND)
        
        valid_statuses = [s[0] for s in FundingRequest.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response({'error': f'Invalid status. Valid options: {valid_statuses}'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Create review record
        from .models import FundingRequestReview
        FundingRequestReview.objects.create(
            funding_request=funding_request,
            reviewer=request.user,
            venture=venture,
            from_status=funding_request.status,
            to_status=new_status,
            notes=notes,
            documents_requested=documents_requested
        )
        
        # Update funding request status
        funding_request.status = new_status
        funding_request.save()
        
        serializer = FundingRequestSerializer(funding_request)
        return Response({'message': 'Status updated', 'funding_request': serializer.data})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def create_negotiation_room(self, request, pk=None):
        """Create a Room for negotiation discussions"""
        venture = self.get_object()
        funding_request_id = request.data.get('funding_request_id')
        
        if not funding_request_id:
            return Response({'error': 'funding_request_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            funding_request = FundingRequest.objects.get(id=funding_request_id)
        except FundingRequest.DoesNotExist:
            return Response({'error': 'Funding request not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if room already exists
        if funding_request.negotiation_room:
            return Response({
                'message': 'Negotiation room already exists',
                'room_id': str(funding_request.negotiation_room.id)
            })
        
        # Create room for negotiation
        from Rooms.models import Room
        room = Room.objects.create(
            name=f"Negotiation: {funding_request.business.name}",
            description=f"Funding negotiation between {venture.name} and {funding_request.business.name}",
            is_private=True,
            require_approval=False
        )
        
        # Add founder and venture creator as members
        room.admins.add(funding_request.business.founder)
        room.admins.add(venture.created_by)
        
        # Link room to funding request
        funding_request.negotiation_room = room
        funding_request.save()
        
        return Response({
            'message': 'Negotiation room created',
            'room_id': str(room.id),
            'room_name': room.name
        })

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def check_agreement(self, request, pk=None):
        """Check if the investor already has a signed agreement for this venture"""
        venture = self.get_object()
        agreement = InvestmentAgreement.objects.filter(
            investor=request.user, venture=venture
        ).first()
        
        if agreement:
            return Response({
                'has_agreement': True,
                'agreement': InvestmentAgreementSerializer(agreement).data
            })
        return Response({
            'has_agreement': False,
            'custom_terms': venture.custom_investment_form or '',
        })

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def sign_agreement(self, request, pk=None):
        """Sign an investment agreement deed — only once per investor per venture"""
        venture = self.get_object()
        
        # Check if already signed
        existing = InvestmentAgreement.objects.filter(
            investor=request.user, venture=venture
        ).first()
        if existing:
            return Response({
                'message': 'Agreement already signed',
                'agreement': InvestmentAgreementSerializer(existing).data
            }, status=status.HTTP_200_OK)
        
        # Validate required fields
        kyc_data = request.data.get('kyc_data', {})
        digital_signature = request.data.get('digital_signature', '')
        
        if not digital_signature:
            return Response(
                {'error': 'digital_signature is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        agreement = InvestmentAgreement.objects.create(
            investor=request.user,
            venture=venture,
            kyc_data=kyc_data,
            digital_signature=digital_signature,
            terms_version=request.data.get('terms_version', 'v1'),
            custom_terms_snapshot=venture.custom_investment_form or '',
            terms_accepted=request.data.get('terms_accepted', True),
            risk_acknowledged=request.data.get('risk_acknowledged', True),
            ethical_compliance=request.data.get('ethical_compliance', True),
            aml_compliance=request.data.get('aml_compliance', True),
        )
        
        return Response({
            'message': 'Investment agreement signed successfully',
            'agreement': InvestmentAgreementSerializer(agreement).data
        }, status=status.HTTP_201_CREATED)


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


# ==============================================================================
# INVESTOR PROFILE
# ==============================================================================

class InvestorProfileView(APIView):
    """GET/POST/PATCH the current user's universal investor profile."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            profile = InvestorProfile.objects.get(user=request.user)
            return Response(InvestorProfileSerializer(profile).data)
        except InvestorProfile.DoesNotExist:
            return Response({'detail': 'No investor profile found.'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        if InvestorProfile.objects.filter(user=request.user).exists():
            return Response({'detail': 'Profile already exists. Use PATCH to update.'},
                            status=status.HTTP_400_BAD_REQUEST)
        serializer = InvestorProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def patch(self, request):
        try:
            profile = InvestorProfile.objects.get(user=request.user)
        except InvestorProfile.DoesNotExist:
            return Response({'detail': 'No investor profile found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = InvestorProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class InvestmentHistoryView(APIView):
    """GET the current user's investment/donation history from completed orders."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from Payment.models import Order, OrderItem
        # Get all orders with funding-type items for this user
        orders = Order.objects.filter(
            buyer__user=request.user,
            items__item_type='funding'
        ).distinct().order_by('-created_at')

        history = []
        for order in orders:
            funding_items = order.items.filter(item_type='funding')
            for item in funding_items:
                history.append({
                    'id': str(order.id),
                    'date': order.created_at.isoformat(),
                    'name': item.name,
                    'amount': str(item.subtotal),
                    'type': item.metadata.get('investment_type', 'equity') if item.metadata else 'equity',
                    'status': order.status,
                    'order_id': str(order.id),
                    'is_donation': item.metadata.get('is_donation', False) if item.metadata else False,
                    'gains': None,  # Placeholder for future gains tracking
                })

        return Response(history)
