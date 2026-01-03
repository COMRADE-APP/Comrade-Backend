"""
Enhanced ViewSets for Events system with comprehensive actions
Includes ticketing, sharing, reactions, room management, and permissions
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from django.utils import timezone
from django.db import transaction
from Events.models import Event, EventTicket
from Events.enhanced_models import (
    EventRoom, EventResourceAccess, EventResourcePurchase,
    EventInterest, EventReaction, EventComment, EventPin,
    EventRepost, EventShare, EventSocialLink, EventBlock,
    EventUserReport, EventTicketPurchase, EventBrowserReminder,
    EventEmailReminder, EventToAnnouncementConversion,
    EventHelpRequest, EventHelpResponse, EventPermission
)
from Events.enhanced_serializers import (
    EventRoomSerializer, EventResourceAccessSerializer, EventResourcePurchaseSerializer,
    EventInterestSerializer, EventReactionSerializer, EventCommentSerializer,
    EventPinSerializer, EventRepostSerializer, EventShareSerializer,
    EventSocialLinkSerializer, EventBlockSerializer, EventUserReportSerializer,
    EventTicketPurchaseSerializer, EventBrowserReminderSerializer,
    EventEmailReminderSerializer, EventConversionSerializer,
    EventHelpRequestSerializer, EventHelpResponseSerializer,
    EventPermissionSerializer, EventDetailSerializer
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
