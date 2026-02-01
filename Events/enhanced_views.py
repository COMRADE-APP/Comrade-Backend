"""
Enhanced ViewSets for Events system with comprehensive actions
Includes ticketing, sharing, reactions, room management, and permissions
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from django.utils import timezone
from django.db import transaction, models
from Events.models import Event, EventTicket
from Events.enhanced_models import (
    EventRoom, EventResourceAccess, EventResourcePurchase,
    EventInterest, EventReaction, EventComment, EventPin,
    EventRepost, EventShare, EventSocialLink, EventBlock,
    EventUserReport, EventTicketPurchase, EventBrowserReminder,
    EventEmailReminder, EventToAnnouncementConversion,
    EventHelpRequest, EventHelpResponse, EventPermission,
    EventDocument, EventArticleLink, EventResearchLink,
    EventAnnouncementLink, EventProductLink, EventPaymentGroupLink
)
from Events.enhanced_serializers import (
    EventRoomSerializer, EventResourceAccessSerializer, EventResourcePurchaseSerializer,
    EventInterestSerializer, EventReactionSerializer, EventCommentSerializer,
    EventPinSerializer, EventRepostSerializer, EventShareSerializer,
    EventSocialLinkSerializer, EventBlockSerializer, EventUserReportSerializer,
    EventTicketPurchaseSerializer, EventBrowserReminderSerializer,
    EventEmailReminderSerializer, EventConversionSerializer,
    EventHelpRequestSerializer, EventHelpResponseSerializer,
    EventPermissionSerializer, EventDetailSerializer,
    EventDocumentSerializer, EventArticleLinkSerializer, EventResearchLinkSerializer,
    EventAnnouncementLinkSerializer, EventProductLinkSerializer, EventPaymentGroupLinkSerializer
)
from Announcements.models import Announcements
from Rooms.models import Room
import secrets


class EventEnhancedViewSet(viewsets.ModelViewSet):
    """
    Enhanced Event ViewSet with comprehensive features
    """
    queryset = Event.objects.all()
    serializer_class = EventDetailSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = Event.objects.all()
        user = self.request.user
        
        # Filter out blocked events for authenticated users
        if user.is_authenticated:
            blocked_event_ids = EventBlock.objects.filter(user=user).values_list('event_id', flat=True)
            queryset = queryset.exclude(id__in=blocked_event_ids)
        
        # Status filter
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Interest filter - show events user is interested in
        if self.request.query_params.get('interested') == 'true' and user.is_authenticated:
            interested_ids = EventInterest.objects.filter(user=user, interested=True).values_list('event_id', flat=True)
            queryset = queryset.filter(id__in=interested_ids)
        
        return queryset.select_related('created_by').prefetch_related('event_reactions', 'event_comments', 'interests')
    
    def perform_create(self, serializer):
        """Auto-set created_by to the authenticated user"""
        print('-----------------------------------------------------------')
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """Get events near a location (within radius_km)"""
        lat = request.query_params.get('latitude')
        lng = request.query_params.get('longitude')
        radius_km = float(request.query_params.get('radius_km', 50))  # Default 50km
        
        if not lat or not lng:
            return Response({'error': 'latitude and longitude are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user_lat = float(lat)
            user_lng = float(lng)
        except ValueError:
            return Response({'error': 'Invalid coordinates'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Simple distance calculation using Haversine formula
        from math import radians, cos, sin, asin, sqrt
        
        def haversine(lon1, lat1, lon2, lat2):
            """Calculate distance in km between two points"""
            lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * asin(sqrt(a))
            r = 6371  # Radius of earth in km
            return c * r
        
        # Get events with coordinates
        events_with_coords = Event.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False,
            status='active'
        )
        
        # Filter by distance
        nearby_events = []
        for event in events_with_coords:
            distance = haversine(user_lng, user_lat, float(event.longitude), float(event.latitude))
            if distance <= radius_km:
                nearby_events.append({
                    'event': event,
                    'distance_km': round(distance, 2)
                })
        
        # Sort by distance
        nearby_events.sort(key=lambda x: x['distance_km'])
        
        # Serialize
        result = []
        for item in nearby_events[:20]:  # Limit to 20 results
            serialized = EventDetailSerializer(item['event']).data
            serialized['distance_km'] = item['distance_km']
            result.append(serialized)
        
        return Response(result)
    
    # TICKET MANAGEMENT (for organizers)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def create_ticket(self, request, pk=None):
        """Create ticket type for event (organizers only)"""
        event = self.get_object()
        
        # Check permissions
        if event.created_by != request.user and not request.user.is_staff:
            perm = EventPermission.objects.filter(event=event, user=request.user, can_manage_tickets=True).first()
            if not perm:
                return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        ticket = EventTicket.objects.create(
            event=event,
            ticket_type=request.data.get('ticket_type', 'regular'),
            price=request.data.get('price', 0),
            quantity_available=request.data.get('quantity', 100),
            qr_code=request.data.get('qr_code', '')
        )
        
        from Events.serializers import EventTicketSerializer
        serializer = EventTicketSerializer(ticket)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def tickets(self, request, pk=None):
        """Get available tickets for event"""
        event = self.get_object()
        tickets = EventTicket.objects.filter(event=event)
        from Events.serializers import EventTicketSerializer
        serializer = EventTicketSerializer(tickets, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def validate_ticket_code(self, request):
        """Validate ticket code for event check-in"""
        ticket_code = request.data.get('ticket_code')
        
        if not ticket_code:
            return Response({'error': 'ticket_code is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find purchase with this code
        purchase = EventTicketPurchase.objects.filter(ticket_codes__contains=[ticket_code]).first()
        
        if not purchase:
            return Response({'valid': False, 'error': 'Invalid ticket code'}, status=status.HTTP_404_NOT_FOUND)
        
        if purchase.is_used:
            return Response({'valid': False, 'error': 'Ticket already used', 'used_at': purchase.used_at})
        
        return Response({
            'valid': True,
            'event': purchase.ticket.event.name,
            'ticket_type': purchase.ticket.ticket_type,
            'user': purchase.user.email
        })
    
    # TICKETING ACTIONS
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def purchase_ticket(self, request, pk=None):
        """Purchase event tickets"""
        event = self.get_object()
        ticket_id = request.data.get('ticket_id')
        quantity = int(request.data.get('quantity', 1))
        payment_option = request.data.get('payment_option')
        
        try:
            ticket = EventTicket.objects.get(id=ticket_id, event=event)
        except EventTicket.DoesNotExist:
            return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check availability
        if ticket.quantity_available < quantity:
            return Response({'error': 'Insufficient tickets available'}, status=status.HTTP_400_BAD_REQUEST)
        
        total_price = ticket.price * quantity
        
        # Create transaction (integrate with Payment system)
        from Payment.models import TransactionToken
        transaction_obj = TransactionToken.objects.create(
            user=request.user.profile,
            amount=total_price,
            payment_option=payment_option,
            category='purchase',
            status='pending'
        )
        
        # Generate unique ticket codes
        ticket_codes = [secrets.token_hex(16).upper() for _ in range(quantity)]
        
        # Create ticket purchase
        purchase = EventTicketPurchase.objects.create(
            ticket=ticket,
            user=request.user,
            quantity=quantity,
            total_price=total_price,
            payment_option=payment_option,
            transaction=transaction_obj,
            payment_status='pending',
            ticket_codes=ticket_codes
        )
        
        # Update ticket availability
        ticket.quantity_available -= quantity
        ticket.save()
        
        serializer = EventTicketPurchaseSerializer(purchase)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def transfer_ticket(self, request):
        """Transfer ticket to another user"""
        purchase_id = request.data.get('purchase_id')
        recipient_email = request.data.get('recipient_email')
        
        if not purchase_id or not recipient_email:
            return Response({'error': 'purchase_id and recipient_email are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            purchase = EventTicketPurchase.objects.get(id=purchase_id, user=request.user)
        except EventTicketPurchase.DoesNotExist:
            return Response({'error': 'Ticket purchase not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if not purchase.is_transferable:
            return Response({'error': 'This ticket is not transferable'}, status=status.HTTP_400_BAD_REQUEST)
        
        if purchase.is_used:
            return Response({'error': 'Cannot transfer used ticket'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find recipient user
        from Authentication.models import CustomUser
        try:
            recipient = CustomUser.objects.get(email=recipient_email)
        except CustomUser.DoesNotExist:
            return Response({'error': 'Recipient user not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Perform transfer
        purchase.transferred_to = recipient
        purchase.transferred_at = timezone.now()
        purchase.user = recipient  # Change ownership
        purchase.save()
        
        serializer = EventTicketPurchaseSerializer(purchase)
        return Response({'message': 'Ticket transferred successfully', 'ticket': serializer.data})
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def refund_ticket(self, request):
        """Request ticket refund"""
        purchase_id = request.data.get('purchase_id')
        reason = request.data.get('reason', '')
        
        if not purchase_id:
            return Response({'error': 'purchase_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            purchase = EventTicketPurchase.objects.get(id=purchase_id, user=request.user)
        except EventTicketPurchase.DoesNotExist:
            return Response({'error': 'Ticket purchase not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if purchase.is_used:
            return Response({'error': 'Cannot refund used ticket'}, status=status.HTTP_400_BAD_REQUEST)
        
        if purchase.payment_status == 'refunded':
            return Response({'error': 'Ticket already refunded'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if event hasn't started yet (allow refund only before event)
        event = purchase.ticket.event
        if event.event_date and event.event_date < timezone.now():
            return Response({'error': 'Cannot refund after event has started'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Mark as refunded and restore ticket availability
        purchase.payment_status = 'refunded'
        purchase.save()
        
        # Restore ticket quantity
        ticket = purchase.ticket
        ticket.quantity_available += purchase.quantity
        ticket.save()
        
        # TODO: Integrate with payment system to process actual refund
        
        return Response({
            'message': 'Refund processed successfully',
            'refund_amount': str(purchase.total_price),
            'reason': reason
        })
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def checkin_ticket(self, request):
        """Check in ticket at event (mark as used)"""
        ticket_code = request.data.get('ticket_code')
        
        if not ticket_code:
            return Response({'error': 'ticket_code is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find purchase with this code
        purchase = EventTicketPurchase.objects.filter(ticket_codes__contains=[ticket_code]).first()
        
        if not purchase:
            return Response({'valid': False, 'error': 'Invalid ticket code'}, status=status.HTTP_404_NOT_FOUND)
        
        if purchase.is_used:
            return Response({'valid': False, 'error': 'Ticket already checked in', 'used_at': purchase.used_at})
        
        # Check if user is authorized to check in (event organizer or has permission)
        event = purchase.ticket.event
        if event.created_by != request.user:
            perm = EventPermission.objects.filter(event=event, user=request.user, can_manage_tickets=True).first()
            if not perm and not request.user.is_staff:
                return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Mark as used
        purchase.is_used = True
        purchase.used_at = timezone.now()
        purchase.save()
        
        return Response({
            'success': True,
            'message': 'Check-in successful',
            'event': event.name,
            'ticket_type': purchase.ticket.ticket_type,
            'attendee': purchase.user.email
        })
    
    # INTEREST & REACTIONS
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def mark_interested(self, request, pk=None):
        """Mark event as interested"""
        event = self.get_object()
        interested = request.data.get('interested', True)
        notify_updates = request.data.get('notify_updates', True)
        
        interest, created = EventInterest.objects.update_or_create(
            event=event,
            user=request.user,
            defaults={
                'interested': interested,
                'notify_updates': notify_updates
            }
        )
        
        serializer = EventInterestSerializer(interest)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_reaction(self, request, pk=None):
        """Add or update reaction to event"""
        event = self.get_object()
        reaction_type = request.data.get('reaction_type')
        
        if not reaction_type:
            return Response({'error': 'reaction_type is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        reaction, created = EventReaction.objects.update_or_create(
            event=event,
            user=request.user,
            defaults={'reaction_type': reaction_type}
        )
        
        serializer = EventReactionSerializer(reaction)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated])
    def remove_reaction(self, request, pk=None):
        """Remove reaction from event"""
        event = self.get_object()
        
        try:
            reaction = EventReaction.objects.get(event=event, user=request.user)
            reaction.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except EventReaction.DoesNotExist:
            return Response({'error': 'Reaction not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # COMMENTS
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_comment(self, request, pk=None):
        """Add comment to event"""
        event = self.get_object()
        content = request.data.get('content')
        parent_id = request.data.get('parent_id')
        
        if not content:
            return Response({'error': 'content is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        comment_data = {
            'event': event,
            'user': request.user,
            'content': content
        }
        
        if parent_id:
            try:
                parent = EventComment.objects.get(id=parent_id)
                comment_data['parent'] = parent
            except EventComment.DoesNotExist:
                return Response({'error': 'Parent comment not found'}, status=status.HTTP_404_NOT_FOUND)
        
        comment = EventComment.objects.create(**comment_data)
        serializer = EventCommentSerializer(comment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        """Get all comments for event"""
        event = self.get_object()
        comments = EventComment.objects.filter(event=event, parent__isnull=True, is_visible=True)
        serializer = EventCommentSerializer(comments, many=True)
        return Response(serializer.data)
    
    # SHARING
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def share(self, request, pk=None):
        """Share event"""
        event = self.get_object()
        share_type = request.data.get('share_type')
        shared_to = request.data.get('shared_to', {})
        
        if not share_type:
            return Response({'error': 'share_type is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        share = EventShare.objects.create(
            event=event,
            user=request.user,
            share_type=share_type,
            shared_to=shared_to
        )
        
        serializer = EventShareSerializer(share)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def generate_share_link(self, request, pk=None):
        """Generate shareable link for event"""
        event = self.get_object()
        platform = request.data.get('platform', '')
        expires_hours = request.data.get('expires_hours')
        
        expires_at = None
        if expires_hours:
            from datetime import timedelta
            expires_at = timezone.now() + timedelta(hours=int(expires_hours))
        
        social_link = EventSocialLink.objects.create(
            event=event,
            created_by=request.user,
            platform=platform,
            expires_at=expires_at
        )
        
        serializer = EventSocialLinkSerializer(social_link)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    # PIN & REPOST
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def pin(self, request, pk=None):
        """Pin event to dashboard"""
        event = self.get_object()
        
        pin, created = EventPin.objects.get_or_create(event=event, user=request.user)
        
        serializer = EventPinSerializer(pin)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated])
    def unpin(self, request, pk=None):
        """Unpin event from dashboard"""
        event = self.get_object()
        
        try:
            pin = EventPin.objects.get(event=event, user=request.user)
            pin.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except EventPin.DoesNotExist:
            return Response({'error': 'Pin not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def repost(self, request, pk=None):
        """Repost event to rooms"""
        event = self.get_object()
        room_ids = request.data.get('room_ids', [])
        caption = request.data.get('caption', '')
        
        repost = EventRepost.objects.create(
            event=event,
            user=request.user,
            caption=caption
        )
        
        if room_ids:
            rooms = Room.objects.filter(id__in=room_ids)
            repost.reposted_to.set(rooms)
        
        serializer = EventRepostSerializer(repost)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    # REPORTING & BLOCKING
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def report(self, request, pk=None):
        """Report event"""
        event = self.get_object()
        report_type = request.data.get('report_type')
        description = request.data.get('description')
        
        if not report_type or not description:
            return Response({'error': 'report_type and description are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        report = EventUserReport.objects.create(
            event=event,
            reporter=request.user,
            report_type=report_type,
            description=description
        )
        
        serializer = EventUserReportSerializer(report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def block(self, request, pk=None):
        """Block event from feed"""
        event = self.get_object()
        reason = request.data.get('reason', '')
        
        block, created = EventBlock.objects.get_or_create(
            event=event,
            user=request.user,
            defaults={'reason': reason}
        )
        
        serializer = EventBlockSerializer(block)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated])
    def unblock(self, request, pk=None):
        """Unblock event"""
        event = self.get_object()
        
        try:
            block = EventBlock.objects.get(event=event, user=request.user)
            block.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except EventBlock.DoesNotExist:
            return Response({'error': 'Block not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # REMINDERS
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def set_reminder(self, request, pk=None):
        """Set event reminder"""
        event = self.get_object()
        reminder_type = request.data.get('type', 'email')  # 'email' or 'browser'
        remind_before = int(request.data.get('remind_before', 24))  # hours or minutes
        
        from datetime import timedelta
        
        if reminder_type == 'browser':
            remind_at = event.event_date - timedelta(minutes=remind_before)
            reminder = EventBrowserReminder.objects.create(
                event=event,
                user=request.user,
                remind_at=remind_at,
                remind_before_minutes=remind_before,
                subscription_info=request.data.get('subscription_info', {})
            )
            serializer = EventBrowserReminderSerializer(reminder)
        else:
            remind_at = event.event_date - timedelta(hours=remind_before)
            reminder = EventEmailReminder.objects.create(
                event=event,
                user=request.user,
                remind_at=remind_at,
                remind_before_hours=remind_before
            )
            serializer = EventEmailReminderSerializer(reminder)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    # ROOM MANAGEMENT
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def toggle_room(self, request, pk=None):
        """Activate/deactivate event room"""
        event = self.get_object()
        
        # Check permissions
        if event.created_by != request.user:
            perm = EventPermission.objects.filter(event=event, user=request.user, can_manage_room=True).first()
            if not perm:
                return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            event_room = event.event_room
            event_room.is_active = not event_room.is_active
            
            if event_room.is_active:
                event_room.activated_at = timezone.now()
                event_room.activated_by = request.user
            else:
                event_room.deactivated_at = timezone.now()
            
            event_room.save()
            
        except EventRoom.DoesNotExist:
            return Response({'error': 'Event room not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = EventRoomSerializer(event_room)
        return Response(serializer.data)
    
    # CONVERSION
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def convert_to_announcement(self, request, pk=None):
        """Convert event to announcement"""
        event = self.get_object()
        
        # Check permissions
        if event.created_by != request.user and not request.user.is_staff:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        retain_event = request.data.get('retain_event', True)
        
        # Create announcement
        announcement = Announcements.objects.create(
            create_by=request.user,
            text=f"{event.name}\n\n{event.description}",
            time=timezone.now()
        )
        
        # Create conversion record
        conversion = EventToAnnouncementConversion.objects.create(
            event=event,
            announcement=announcement,
            converted_by=request.user,
            retain_event=retain_event
        )
        
        if not retain_event:
            event.status = 'archived'
            event.save()
        
        serializer = EventConversionSerializer(conversion)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    # HELP SYSTEM
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def request_help(self, request, pk=None):
        """Request help from event organizers"""
        event = self.get_object()
        subject = request.data.get('subject')
        message = request.data.get('message')
        priority = request.data.get('priority', 'medium')
        
        if not subject or not message:
            return Response({'error': 'subject and message are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        help_request = EventHelpRequest.objects.create(
            event=event,
            user=request.user,
            subject=subject,
            message=message,
            priority=priority
        )
        
        serializer = EventHelpRequestSerializer(help_request)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def help_requests(self, request, pk=None):
        """Get help requests for event (organizers only)"""
        event = self.get_object()
        
        # Check if user is organizer or has permission
        if event.created_by != request.user:
            perm = EventPermission.objects.filter(event=event, user=request.user, can_respond_to_help=True).first()
            if not perm and not request.user.is_staff:
                return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        requests = EventHelpRequest.objects.filter(event=event)
        serializer = EventHelpRequestSerializer(requests, many=True)
        return Response(serializer.data)


# ===== LOGISTICS VIEWSETS =====

class EventDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for event document management"""
    queryset = EventDocument.objects.all()
    serializer_class = EventDocumentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = EventDocument.objects.filter(is_archived=False)
        event_id = self.request.query_params.get('event')
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        
        # Filter by visibility
        user = self.request.user
        if not user.is_authenticated:
            queryset = queryset.filter(visibility='public')
        else:
            queryset = queryset.filter(
                models.Q(visibility='public') | 
                models.Q(visibility='attendees') |
                models.Q(event__created_by=user)
            )
        
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['post'], url_path='download')
    def download(self, request, pk=None):
        """Track document download"""
        document = self.get_object()
        document.download_count = models.F('download_count') + 1
        document.save(update_fields=['download_count'])
        
        serializer = self.get_serializer(document)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def archive(self, request, pk=None):
        """Archive document"""
        document = self.get_object()
        if document.uploaded_by != request.user and document.event.created_by != request.user:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        document.is_archived = True
        document.save()
        return Response({'status': 'archived'})


class EventArticleLinkViewSet(viewsets.ModelViewSet):
    """ViewSet for linking articles to events"""
    queryset = EventArticleLink.objects.all()
    serializer_class = EventArticleLinkSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = EventArticleLink.objects.all()
        event_id = self.request.query_params.get('event')
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        link_type = self.request.query_params.get('link_type')
        if link_type:
            queryset = queryset.filter(link_type=link_type)
        return queryset.order_by('-created_at')


class EventResearchLinkViewSet(viewsets.ModelViewSet):
    """ViewSet for linking research to events"""
    queryset = EventResearchLink.objects.all()
    serializer_class = EventResearchLinkSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = EventResearchLink.objects.all()
        event_id = self.request.query_params.get('event')
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        return queryset.order_by('presentation_order')


class EventAnnouncementLinkViewSet(viewsets.ModelViewSet):
    """ViewSet for linking announcements to events"""
    queryset = EventAnnouncementLink.objects.all()
    serializer_class = EventAnnouncementLinkSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = EventAnnouncementLink.objects.all()
        event_id = self.request.query_params.get('event')
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        return queryset.order_by('-created_at')


class EventProductLinkViewSet(viewsets.ModelViewSet):
    """ViewSet for linking products to events"""
    queryset = EventProductLink.objects.all()
    serializer_class = EventProductLinkSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = EventProductLink.objects.all()
        event_id = self.request.query_params.get('event')
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        
        # Filter by availability
        now = timezone.now()
        available_only = self.request.query_params.get('available', 'false').lower() == 'true'
        if available_only:
            queryset = queryset.filter(
                models.Q(available_from__isnull=True) | models.Q(available_from__lte=now),
                models.Q(available_until__isnull=True) | models.Q(available_until__gte=now)
            )
        
        return queryset.order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def exclusive(self, request):
        """Get exclusive event products"""
        event_id = request.query_params.get('event')
        queryset = self.get_queryset().filter(is_exclusive=True)
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class EventPaymentGroupLinkViewSet(viewsets.ModelViewSet):
    """ViewSet for linking payment groups (piggy banks) to events"""
    queryset = EventPaymentGroupLink.objects.all()
    serializer_class = EventPaymentGroupLinkSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = EventPaymentGroupLink.objects.all()
        event_id = self.request.query_params.get('event')
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        purpose = self.request.query_params.get('purpose')
        if purpose:
            queryset = queryset.filter(purpose=purpose)
        return queryset.order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def progress(self, request):
        """Get funding progress for event payment groups"""
        event_id = request.query_params.get('event')
        if not event_id:
            return Response({'error': 'event parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        links = EventPaymentGroupLink.objects.filter(event_id=event_id).select_related('payment_group')
        
        total_target = sum(link.target_amount for link in links)
        total_collected = sum(link.payment_group.total_collected or 0 for link in links)
        progress_percentage = (total_collected / total_target * 100) if total_target > 0 else 0
        
        return Response({
            'event_id': event_id,
            'total_target': total_target,
            'total_collected': total_collected,
            'progress_percentage': round(progress_percentage, 2),
            'groups_count': links.count()
        })
