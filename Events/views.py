from django.shortcuts import render
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ModelViewSet
from Events.serializers import EventSerializer
from Events.models import Event, EventCategory, EventAttendance, EventBudget, EventCategoryAssignment, EventCollaboration, EventFeedback, EventFeedbackResponse, EventFile, EventFollowUp, EventLogistics, EventMediaCoverage, EventPartnership, EventPhoto, EventPromotion, EventRegistration, EventReminder, EventSchedule, EventSession, EventSpeaker, EventSponsor, EventSponsorAgreement, EventSponsorBenefit, EventSponsorLogo, EventSponsorPackage, EventSponsorPayment, EventSponsorshipAgreementDocument, EventSponsorshipApplication, EventSponsorshipApproval, EventSponsorshipCertificate, EventSponsorshipContract, EventSponsorshipDowngrade, EventSponsorshipEvaluation, EventSponsorshipExtension, EventSponsorshipFeedback, EventSponsorshipHistory, EventSponsorshipInvoice, EventSponsorshipLetter, EventSponsorshipLevel, EventSponsorshipRecognition, EventSponsorshipRejection, EventSponsorshipRenewal, EventSponsorshipReport, EventSponsorshipTermination, EventSponsorshipTransfer, EventSponsorshipUpgrade, EventSurvey, EventSurveyQuestion, EventSurveyResponse, EventTag, EventTagAssignment, EventTicket, EventVideo, EventReport, EventInvitation, EventLike, EventVisibility, VisibilityLog, EventSlotBooking, TicketTier, EventInteractionAnalytics, EventMaterial
from Events.serializers import EventSerializer, EventCategorySerializer, EventAttendanceSerializer, EventBudgetSerializer, EventCategoryAssignmentSerializer, EventCollaborationSerializer, EventFeedbackSerializer, EventFeedbackResponseSerializer, EventFileSerializer, EventFollowUpSerializer, EventLogisticsSerializer, EventMediaCoverageSerializer, EventPartnershipSerializer, EventPhotoSerializer, EventPromotionSerializer, EventRegistrationSerializer, EventReminderSerializer, EventScheduleSerializer, EventSessionSerializer, EventSpeakerSerializer, EventSponsorSerializer, EventSponsorAgreementSerializer, EventSponsorBenefitSerializer, EventSponsorLogoSerializer, EventSponsorPackageSerializer, EventSponsorPaymentSerializer, EventSponsorshipAgreementDocumentSerializer, EventSponsorshipApplicationSerializer, EventSponsorshipApprovalSerializer, EventSponsorshipCertificateSerializer, EventSponsorshipContractSerializer, EventSponsorshipDowngradeSerializer, EventSponsorshipEvaluationSerializer, EventSponsorshipExtensionSerializer, EventSponsorshipFeedbackSerializer, EventSponsorshipHistorySerializer, EventSponsorshipInvoiceSerializer, EventSponsorshipLetterSerializer, EventSponsorshipLevelSerializer, EventSponsorshipRecognitionSerializer, EventSponsorshipRejectionSerializer, EventSponsorshipRenewalSerializer, EventSponsorshipReportSerializer, EventSponsorshipTerminationSerializer, EventSponsorshipTransferSerializer, EventSponsorshipUpgradeSerializer, EventSurveySerializer, EventSurveyQuestionSerializer, EventSurveyResponseSerializer, EventTagSerializer, EventTagAssignmentSerializer, EventTicketSerializer, EventVideoSerializer, EventReportSerializer, EventInvitationSerializer, EventLikeSerializer, EventVisibilitySerializer, VisibilityLogSerializer, EventSlotBookingSerializer, EventInteractionAnalyticsSerializer
from Announcements.models import Pin
from Rooms.permissions import IsModerator
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from datetime import datetime
from Events.models import EventReport
from threading import Thread
from django.utils import timezone
import time
from Authentication.models import Profile, CustomUser
from Authentication.serializers import ProfileSerializer
from Rooms.models import Room, DefaultRoom, DirectMessage
from urllib.parse import quote
from django.core.mail import send_mail
from django.conf import settings
import copy
from django.shortcuts import get_object_or_404
from Resources.views import VISIBILITY_MAP
import json
import PyPDF2

# Create your views here.


class EventViewSet(ModelViewSet):
    serializer_class = EventSerializer
    queryset = Event.objects.all().order_by('-time_stamp')
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination
    filter_backends = [SearchFilter, OrderingFilter]
    lookup_field = 'id'
    search_fields = ['id', 'name', 'description', 'location']
    filterset_fields = ['event_date', 'location', 'created_by', 'status', 'complexity_level']

    def _process_nested_data(self, event, request_data):
        # Process Ticket Tiers
        ticket_tiers_data = request_data.get('ticket_tiers', [])
        if isinstance(ticket_tiers_data, str):
            try:
                ticket_tiers_data = json.loads(ticket_tiers_data)
            except json.JSONDecodeError:
                ticket_tiers_data = []
        
        if ticket_tiers_data:
            # Clear existing if updating (or handle more gracefully)
            event.ticket_tiers.all().delete()
            for tier_data in ticket_tiers_data:
                TicketTier.objects.create(
                    event=event,
                    name=tier_data.get('name'),
                    price=tier_data.get('price', 0.00),
                    capacity=tier_data.get('capacity', 0),
                    min_age=tier_data.get('min_age'),
                    max_age=tier_data.get('max_age'),
                    custom_criteria=tier_data.get('custom_criteria', ''),
                    group_size_allowed=tier_data.get('group_size_allowed', 1)
                )

        # Process Materials via IDs
        materials_ids = request_data.getlist('existing_materials', []) if hasattr(request_data, 'getlist') else request_data.get('existing_materials', [])
        if materials_ids:
            try:
                # Assuming materials were uploaded separately and we're just linking them
                mats = EventMaterial.objects.filter(id__in=materials_ids)
                event.materials.add(*mats)
            except Exception:
                pass


    def create(self, request, *args, **kwargs):
        # Allow DRF to handle the main model creation
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        event = serializer.instance
        self._process_nested_data(event, request.data)

        headers = self.get_success_headers(serializer.data)
        return Response(self.get_serializer(event).data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        self._process_nested_data(instance, request.data)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(self.get_serializer(instance).data)

    def perform_create(self, serializer):
        """Auto-set created_by to the authenticated user and optionally link to a room"""
        instance = serializer.save(created_by=self.request.user)
        
        # Auto-create Event Kitty (PaymentGroup)
        try:
            from Payment.models import PaymentGroups
            from django.contrib.contenttypes.models import ContentType
            
            content_type = ContentType.objects.get_for_model(instance)
            group_name = instance.event_organizer.name if instance.event_organizer else f"Event Kitty - {instance.name}"
            # Ensure name fits in PaymentGroup name field (max 100)
            if len(group_name) > 100:
                group_name = group_name[:97] + '...'
            
            PaymentGroups.objects.create(
                name=group_name,
                owner=self.request.user,
                content_type=content_type,
                object_id=instance.id,
                target_amount=0.00
            )
        except Exception as e:
            print(f"Failed to auto-create event kitty: {e}")

        # Check if room parameter was provided
        room_id = self.request.data.get('room')
        if room_id:
            try:
                room = Room.objects.get(pk=room_id)
                room.events.add(instance)
            except Room.DoesNotExist:
                pass  # Silently ignore invalid room ID

    # @action(detail=False, methods=['get'])
    # def create_event(self, request):
    # ... (existing commented code)
    #     return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='parse-document')
    def parse_document(self, request):
        """
        AI-powered document parsing to auto-fill event fields.
        Expects a file upload (PDF/Text) and returns extracted JSON data.
        """
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        extracted_text = ""
        try:
            if file_obj.name.endswith('.pdf'):
                pdf_reader = PyPDF2.PdfReader(file_obj)
                for page in pdf_reader.pages:
                    extracted_text += page.extract_text() + "\n"
            else:
                extracted_text = file_obj.read().decode('utf-8', errors='ignore')
        except Exception as e:
            return Response({"error": f"Failed to read file: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        # MOCK LLM EXTRACTION
        # In production, send `extracted_text` to QomAI/LLM to retrieve structured JSON
        # For this prototype, we'll run a basic heuristic/mock extraction
        
        parsed_data = {
            "name": "Auto-Extracted Event Title",
            "description": extracted_text[:500] + "...",  # First 500 chars as description
            "location": "TBD Location",
            "event_date": timezone.now().date().isoformat(),
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "capacity": 100,
            "is_ticketed": False,
            "seeking_sponsors": "sponsor" in extracted_text.lower(),
            "seeking_partners": "partner" in extracted_text.lower()
        }

        return Response({
            "message": "Document parsed successfully",
            "parsed_data": parsed_data,
            "raw_text_preview": extracted_text[:200]
        }, status=status.HTTP_200_OK)

    # Custom user actions
    '''Actions for normal users to interact with events such as RSVP, comment, like, etc.'''
    @action(detail=False, methods=['get'])
    def my_events(self, request):
        user = request.user
        events = Event.objects.filter(created_by=user)
        page = self.paginate_queryset(events)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def upcoming_events(self, request):
        now = timezone.now()
        events = Event.objects.filter(event_date__gte=now).order_by('event_date')
        page = self.paginate_queryset(events)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def past_events(self, request):
        now = timezone.now()
        events = Event.objects.filter(event_date__lt=now).order_by('-event_date')
        page = self.paginate_queryset(events)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def rsvp(self, request, name=None):
        event = self.get_object()
        user = request.user
        event.attendees.add(user)
        event.save()
        return Response({'status': 'RSVP successful'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def cancel_rsvp(self, request, name=None):
        event = self.get_object()
        user = request.user
        event.attendees.remove(user)
        event.save()
        return Response({'status': 'RSVP cancelled'}, status=status.HTTP_200_OK)
    
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def bookmark(self, request, name=None):
        event = self.get_object()
        user = request.user
        bookmarked_events = Pin.objects.create(user=user, event=event)
        bookmarked_events.save()
        return Response({'status': 'Event bookmarked'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def remove_bookmark(self, request, name=None):
        event = self.get_object()
        user = request.user
        Pin.objects.filter(user=user, event=event).delete()
        return Response({'status': 'Bookmark removed'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def is_bookmarked(self, request, name=None):  
        event = self.get_object()
        user = request.user
        is_bookmarked = Pin.objects.filter(user=user, events=event).exists()
        return Response({'is_bookmarked': is_bookmarked}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def attendees(self, request, name=None):
        event = self.get_object()
        attendees = event.attendees.all()
        attendees_data = [{'last_name': attendee.last_name, 'first_name': attendee.first_name} for attendee in attendees]
        return Response(attendees_data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def attendee_count(self, request, name=None):
        event = self.get_object()
        count = event.attendees.count()
        return Response({'attendee_count': count}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def share(self, request, name=None):
        event = self.get_object()
        platform = request.data.get('platform')
        link = request.data.get('link')
        # Implement sharing logic here (e.g., generate shareable link, integrate with social media APIs)
        # shareable_link = f"http://example.com/events/{event.id}/"
        sharing_option = request.data.get('sharing_option')

        if sharing_option == 'copied':
            # Return the link for client-side clipboard copying
            return Response({
            'action': 'copy',
            'link': link or f'http://example.com/events/{event.id}/',
            'message': 'Link copied to clipboard'
            }, status=status.HTTP_200_OK)

        elif sharing_option == 'social_media':
            text = request.data.get('text', '')
            encoded_url = quote(link or f'http://example.com/events/{event.id}/', safe='')
            encoded_text = quote(text, safe='')

            # Social media share URLs
            share_urls = {
            'whatsapp': f'https://wa.me/?text={encoded_text}%20{encoded_url}' if text else f'https://wa.me/?text={encoded_url}',
            'x': f'https://x.com/intent/tweet?text={encoded_text}%20{encoded_url}' if text else f'https://x.com/intent/tweet?text={encoded_url}',
            'facebook': f'https://www.facebook.com/sharer/sharer.php?u={encoded_url}',
            'tiktok': f'https://www.tiktok.com/share?url={encoded_url}',
            'instagram': f'https://www.instagram.com/?url={encoded_url}',
            'signal': f'https://signal.me/#p?text={encoded_text}%20{encoded_url}' if text else f'https://signal.me/#p?text={encoded_url}',
            }

            platform_key = (platform or '').lower()
            share_url = share_urls.get(platform_key)

            if share_url:
                return Response({
                    'action': 'redirect',
                    'platform': platform_key,
                    'share_url': share_url
                }, status=status.HTTP_200_OK)

            return Response({
            'error': 'Unsupported social platform',
            'supported_platforms': list(share_urls.keys())
            }, status=status.HTTP_400_BAD_REQUEST)


        return Response({'status': f'Event shared on {platform}', 'link': link}, status=status.HTTP_200_OK)
    



    

    
    # Moderator/Admin actions
    '''Actions for admin/moderator users to manage events such as approve, reject, feature, etc.'''
    @action(detail=True, methods=['put', 'patch'])
    def schedule_event(self, request, name=None):
        '''Schedule events'''
        event_id = request.data.get('id')
        event = Event.objects.get(id=event_id)
        serializer = EventSerializer(event, data=request.data, partial=(request.method == 'PATCH'))
        
        if not serializer.is_valid():
            return Response({'error': f'The input data is not valid. Check the errors below:\n{serializer.errors}'}, status=status.HTTP_400_BAD_REQUEST)
        
        scheduled_time = serializer.validated_data.get('scheduled_time')
        if scheduled_time:
            event.scheduled_time = scheduled_time
            event.save()
            
            # Start a background thread to check when scheduled time is reached
            thread = Thread(target=self._schedule_event_posting, args=(event.id,))
            thread.daemon = True
            thread.start()
            
            return Response({'status': 'Event scheduled successfully'}, status=status.HTTP_200_OK)
        return Response({'error': 'Scheduled time is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    def _schedule_event_posting(self, event_id):
        """Background thread to post event when scheduled time is reached"""
        
        event = Event.objects.get(id=event_id)
        
        while True:
            now = timezone.now()
            if event.scheduled_time and now >= event.scheduled_time:
                # Post the event
                event.is_posted = True
                event.posted_at = now
                event.save()
                break
            
            # Check every minute
            time.sleep(60)
        return Response({'error': 'Scheduled time is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    
    @action(detail=True, methods=['post', 'put', 'patch'])
    def set_deadlines(self, request):
        '''Set booking deadlines'''
        event_id = request.data.get('event_id')
        deadline = request.data.get('deadline')
        if not event_id:
            return Response({'error': 'Event Id needs to be passed.'})
        
        if not deadline:
            return Response({'error': 'Event booking deadline needs to be set.'})
        

        def dealine_checker(event_id, target_time):
            try:
                while True:
                    now = datetime.now()
                    if target_time <= now:
                        try:
                            event = Event.objects.get(id=event_id)
                            event.deadline_reached = True
                            event.booking_status = 'closed'
                            event.save()
                        except Event.DoesNotExist:
                            pass
                    break
                time.sleep(1)
            except:
                return
        
        deadline_thread = Thread(target=dealine_checker, args=(event_id, deadline), daemon=True)
        deadline_thread.start()

        return Response({
            'message': f'The deadline for the event has reached.',
            'event_id': event_id
        }, status=status.HTTP_200_OK)


    @action(detail=True, methods=['post', 'put', 'patch'])
    def set_event_expiry(self, request):
        '''Set event expiry'''
        '''Set booking deadlines'''
        event_id = request.data.get('event_id')
        expiry = request.data.get('expiry')
        if not event_id:
            return Response({'error': 'Event Id needs to be passed.'})
        
        if not expiry:
            return Response({'error': 'Event booking expiry needs to be set.'})
        

        def dealine_checker(event_id, target_time):
            try:
                while True:
                    now = datetime.now()
                    if target_time <= now:
                        try:
                            event = Event.objects.get(id=event_id)
                            event.deadline_reached = True
                            event.booking_status = 'closed'
                            event.save()
                        except Event.DoesNotExist:
                            pass
                    break
                time.sleep(1)
            except:
                return
        
        expiry_thread = Thread(target=dealine_checker, args=(event_id, expiry), daemon=True)
        expiry_thread.start()

        return Response({
            'message': f'The expiry for the event has reached.',
            'event_id': event_id
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post', 'put', 'patch'])
    def set_reminder(self, request):
        '''Set reminders'''
        event = self.get_object()
        event_id = request.data.get('event_id')
        notification_period = request.data.get('notification_period')

        if not notification_period:
            return Response({'error': 'The notification period for the event is suppossed to be set.'}, status=status.HTTP_403_FORBIDDEN)

        event_date = event.event_date
        try:
            event_date = Event.objects.get(id=event_id).event_date
            reminder_date = event_date.minute - notification_period

        except Event.DoesNotExist:
            return Response({'error': 'The event does not exist.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        def _set_reminder(event, reminder_date):
            try:
                while True:
                    now = datetime.now()
                    if reminder_date <= now:
                        try:
                            # TODO: reminder sent to the user (logic should be here)
                            user = request.user
                            user = Profile.objects.get(user=user)
                            email = user.user.email
                            send_mail(f'Reminder: The {event.name} is around the corner.', f'Click to view the event: http://121.0.0.1/events/event/{event.id}', settings.DEFAULT_FROM_EMAIL, [email])
                        except Exception as e:
                            pass
                    break
                time.sleep(1)
            except Exception as e:
                return
        

        Thread(target=_set_reminder, args=(event, reminder_date), daemon=True)
        Thread.start()

        return Response({'message': f'A reminder was sent to the user email ({request.user.email}).'}, status=status.HTTP_200_OK)
    
    # from the normal user
    @action(detail=True, methods=['post'])
    def block_creator_content(self, request):
        '''Block according to the creator'''
        # TODO: choose the identifier for the creator to be identify them easily
        creator_email = request.data.get('creator_email')

        try:
            creator = CustomUser.objects.get(email=creator_email)
            user = CustomUser.objects.get(email=request.user.email)

        except CustomUser.DoesNotExist:
            return Response({'error': f'User with the email {creator_email} does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            blocked_events = Event.objects.filter(created_by=creator)
            profile = Profile.objects.get(user=user)
            profile.blocked_events.add(blocked_events)
            profile.save()

            return Response({'message': f'Events from {profile.user.first_name} {profile.user.last_name} has been blocked. Click on blocked events to view them.'}, status=status.HTTP_200_OK)

        except Event.DoesNotExist:
            return Response({'error': 'The creator does not has not created any events yet.'}, status=status.HTTP_404_NOT_FOUND)
        
    # Set members to viewable
    @action(detail=True, methods=['post'])
    def activate_attendees_view(self, request, name=None):
        event = self.get_object()

        if not event:
            return Response({'error': 'No event was detected.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        event.attendees_viewable = True
        event.save()
        # attendees = ProfileSerializer(data=(event.attendees), many=True)
        data = {f'{attendee.first_name} {attendee.last_name}' for attendee in event.attendees}
        data['message'] = f'Attendees for the event ({event.name}) are now viewable.'

        return Response(data, status=status.HTTP_200_OK)
    
    # Deactivate the event feedback giving
    @action(detail=True, methods=['post'])
    def deactivate_feedback(self, request, name=None):
        event = self.get_object()

        if not event:
            return Response({'error': 'No event was detected.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        event.activate_feedback = False
        event.save()
        # attendees = ProfileSerializer(data=(event.attendees), many=True)
        data = {f'{attendee.first_name} {attendee.last_name}' for attendee in event.attendees}
        data['message'] = f'Attendees for the event ({event.name}) are now viewable.'

        return Response(data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def duplicate_event(self, request, name=None):
        """ Duplicate Events Attrributes"""
        event = EventSerializer(data=request.data)
        event.validated_data.pop('id')
        event.save()
        return Response({'message': 'Event duplicated successfully. Saved as draft.'}, status=status.HTTP_201_CREATED)

    # ===== REACTIONS (love, excited) =====

    @action(detail=True, methods=['post'], url_path='add_reaction')
    def add_reaction(self, request, id=None):
        """Add or update a reaction to an event."""
        event = self.get_object()
        reaction_type = request.data.get('reaction_type', 'love')
        like_obj, created = EventLike.objects.get_or_create(
            event=event, user=request.user,
            defaults={'reaction': reaction_type, 'like': True}
        )
        if not created:
            like_obj.reaction = reaction_type
            like_obj.like = True
            like_obj.save()
        return Response({
            'status': 'reaction_added',
            'reaction_type': reaction_type,
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'], url_path='remove_reaction')
    def remove_reaction(self, request, id=None):
        """Remove a reaction from an event."""
        event = self.get_object()
        EventLike.objects.filter(event=event, user=request.user).delete()
        return Response({'status': 'reaction_removed'}, status=status.HTTP_200_OK)

    # ===== PIN / UNPIN =====

    @action(detail=True, methods=['post'], url_path='pin')
    def pin_event(self, request, id=None):
        """Pin event to user's dashboard."""
        event = self.get_object()
        pin_obj, created = Pin.objects.get_or_create(user=request.user)
        pin_obj.events.add(event)
        return Response({'status': 'pinned'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'], url_path='unpin')
    def unpin_event(self, request, id=None):
        """Unpin event from user's dashboard."""
        event = self.get_object()
        pins = Pin.objects.filter(user=request.user)
        for pin in pins:
            pin.events.remove(event)
        return Response({'status': 'unpinned'}, status=status.HTTP_200_OK)

    # ===== INTERESTED =====

    @action(detail=True, methods=['post'], url_path='mark_interested')
    def mark_interested(self, request, id=None):
        """Toggle interest in an event using EventFeedback with attendance_status=interested."""
        event = self.get_object()
        interested = request.data.get('interested', True)
        if interested:
            EventFeedback.objects.get_or_create(
                event=event, user=request.user,
                defaults={'attendendance_status': 'interested', 'rating': 0}
            )
        else:
            EventFeedback.objects.filter(
                event=event, user=request.user, attendendance_status='interested'
            ).delete()
        return Response({'status': 'interested' if interested else 'not_interested'}, status=status.HTTP_200_OK)


class EventVisibilityViewSet(ModelViewSet):
    serializer_class = EventVisibilitySerializer
    queryset = EventVisibility.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

    # @action(detail=True, methods=['post'])
    # def create_visibility(self, request):
    #     '''Set material availability period'''
    #     pass
    
    # '''Add to blocked list'''
    # '''Restrict rooms'''
     # Creating a visibility and logging it (for the first time).
    @action(detail=True, methods=['post'])
    def create_visibility(self, request):
        event_id = request.data.get("event_id")
        visibility_groups = request.data.get("visibility", {})

        if not event_id:
            return Response({"error": "event_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        event = get_object_or_404(Event, id=event_id)

        visibility, created = EventVisibility.objects.get_or_create(event=event)
        old_visibility = None  # No previous visibility for creation
        changed_by = request.user

        for group_name, ids in visibility_groups.items():

            if group_name not in VISIBILITY_MAP:
                return Response({
                    "error": f"Invalid visibility type: {group_name}"
                }, status=status.HTTP_400_BAD_REQUEST)

            model, field_name = VISIBILITY_MAP[group_name]

            # Fetch all objects matching the IDs
            objects = model.objects.filter(id__in=ids)

            if objects.count() != len(ids):
                return Response({
                    "error": f"Some IDs in {group_name} do not exist."
                }, status=status.HTTP_400_BAD_REQUEST)

            # Add to the many-to-many field
            getattr(visibility, field_name).add(*objects)

        visibility.save()
        new_visibility = copy.copy(visibility)
        try:
            VisibilityLog.objects.create(
                event=event,
                old_visibility=old_visibility,
                new_visibility=new_visibility,
                changed_by=changed_by
            )
            return Response({
                "message": "Visibility created successfully and logged.", "visibility": visibility_groups
            }, status=201)
        except Exception as e:
            return Response({
                "error": f"Failed to log visibility creation: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    #
    @action(detail=True, methods=['patch', 'put'])
    def remove_visibility(self, request, pk=None):
        visibility_id = request.data.get("visibility_id")
        visibility_groups = request.data.get("visibility", {})

        if not visibility_id:
            return Response({"error": "visibility_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        visibility = get_object_or_404(EventVisibility, id=visibility_id)
        if not visibility:
            return Response({"error": "EventVisibility not found."}, status=404)

        old_visibility = copy.copy(visibility)

        for group_name, ids in visibility_groups.items():

            if group_name not in VISIBILITY_MAP:
                return Response({
                    "error": f"Invalid visibility type: {group_name}"
                }, status=status.HTTP_400_BAD_REQUEST)

            model, field_name = VISIBILITY_MAP[group_name]

            # Fetch all objects matching the IDs
            objects = model.objects.filter(id__in=ids)

            if objects.count() != len(ids):
                return Response({
                    "error": f"Some IDs in {group_name} do not exist."
                }, status=status.HTTP_400_BAD_REQUEST)

            # Remove from the many-to-many field
            getattr(visibility, field_name).remove(*objects)

        visibility.save()
        new_visibility = copy.copy(visibility)
        changed_by = request.user

        try:
            if old_visibility != new_visibility:
                VisibilityLog.objects.create(
                    event=visibility.event,
                    old_visibility=old_visibility,
                    new_visibility=new_visibility,
                    changed_by=changed_by
                )
                return Response({
                        "message": "Visibility items removed successfully. The action has been logged.",
                        "removed": visibility_groups
                    }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "error": f"Failed to log visibility change: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)        

    
    # @action(detail=True, methods=['patch', 'put'])
    # def add_visibility(self, request, pk=None):
    #     visibility_id = request.data.get("visibility_id")
    #     visibility_groups = request.data.get("visibility", {})

    #     if not visibility_id:
    #         return Response({"error": "visibility_id is required."}, status=status.HTTP_400_BAD_REQUEST)

    #     visibility = get_object_or_404(EventVisibility, id=visibility_id)

    #     for group_name, ids in visibility_groups.items():

    #         if group_name not in VISIBILITY_MAP:
    #             return Response({
    #                 "error": f"Invalid visibility type: {group_name}"
    #             }, status=status.HTTP_400_BAD_REQUEST)

    #         model, field_name = VISIBILITY_MAP[group_name]

    #         # Fetch all objects matching the IDs
    #         objects = model.objects.filter(id__in=ids)

    #         if objects.count() != len(ids):
    #             return Response({
    #                 "error": f"Some IDs in {group_name} do not exist."
    #             }, status=status.HTTP_400_BAD_REQUEST)

    #         # Add to the many-to-many field
    #         getattr(visibility, field_name).add(*objects)

    #     visibility.save()

    #     return Response({
    #         "message": "Visibility items added successfully.",
    #         "added": visibility_groups
    #     }, status=status.HTTP_200_OK)
    
    # Make a event public
    @action(detail=True, methods=['post', 'put', 'patch'])
    def make_public(self, request, pk=None):
        visibility_id = request.data.get("visibility_id")
        if not visibility_id:
            return Response({"error": "visibility_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        visibility = get_object_or_404(EventVisibility, id=visibility_id)
        old_visibility = visibility
        created_by = request.user
        
        visibility.event.visibility = 'public'
        visibility.event.save()
        visibility.save()
        new_visibility = copy.copy(visibility)

        try:
            VisibilityLog.objects.create(
                event=visibility.event,
                old_visibility=old_visibility,
                new_visibility=new_visibility,
                changed_by=created_by
            )
            return Response({
                "message": "event made public successfully and logged."
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "error": f"Failed to log making event public: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @action(detail=False, methods=['post', 'put', 'patch'])
    def set_duration_availability(self, request):
        visibility_id = request.data.get("visibility_id")
        visibility_groups = request.data.get("visibility", {})
        expiry_time = request.data.get('expiry_time')
        

        if not visibility_id:
            return Response({"error": "visibility_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        visibility = get_object_or_404(EventVisibility, id=visibility_id)
        old_visibility = copy.copy(visibility)
        created_by = request.user


        for group_name, ids in visibility_groups.items():

            if group_name not in VISIBILITY_MAP:
                return Response({
                    "error": f"Invalid visibility type: {group_name}"
                }, status=status.HTTP_400_BAD_REQUEST)

            model, field_name = VISIBILITY_MAP[group_name]

            # Fetch all objects matching the IDs
            objects = model.objects.filter(id__in=ids)

            if objects.count() != len(ids):
                return Response({
                    "error": f"Some IDs in {group_name} do not exist."
                }, status=status.HTTP_400_BAD_REQUEST)

            # Add to the many-to-many field
            getattr(visibility, field_name).add(*objects)

        visibility.save()
        new_visibility = copy.copy(visibility)

        VisibilityLog.objects.create(
                event=visibility.event,
                old_visibility=old_visibility,
                new_visibility=new_visibility,
                changed_by=created_by
            )

        # check if expiry time is reached
        def _expiry_checker(visibility_id, target_time):
            try:
                while True:
                    now = datetime.now()
                    if now >= target_time:
                        try:
                            visibility = EventVisibility.objects.get(pk=visibility_id)
                            # remove the visibility
                            getattr(visibility, field_name).remove(*objects)
                            VisibilityLog.objects.create(
                                event=visibility.event,
                                old_visibility=new_visibility,
                                new_visibility=old_visibility,
                                changed_by=created_by
                            )
                            visibility.save()
                        except EventVisibility.DoesNotExist:
                            pass
                    break
                time.sleep(1)
            except Exception:
                # fail silently for background checker
                return

        checker_thread = Thread(target=_expiry_checker, args=(visibility_id, expiry_time), daemon=True)
        checker_thread.start()

        return Response({
            "message": "Visibility items added successfully.",
            "added": visibility_groups
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post', 'put', 'patch'])
    def schedule_visibility(self, request):
        visibility_id = request.data.get("visibility_id")
        visibility_groups = request.data.get("visibility", {})
        expiry_time = request.data.get('expiry_time')
        event_id = request.data.get('event_id')
        

        if not expiry_time:
            return Response({"error": "Expiry time is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not event_id:
            return Response({"error": "event is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not visibility_id and event_id:
            event = get_object_or_404(Event, id=event_id)

            visibility = EventVisibility.objects.create(event=event, expiry_time=expiry_time)
        else:
            visibility = get_object_or_404(EventVisibility, id=visibility_id)

        old_visibility = copy.copy(visibility)
        created_by = request.user


        # check if expiry time is reached
        def _schedule_checker(visibility_id, target_time):
            try:
                while True:
                    now = datetime.now()
                    if now >= target_time:
                        try:
                             for group_name, ids in visibility_groups.items():

                                if group_name not in VISIBILITY_MAP:
                                    return Response({
                                        "error": f"Invalid visibility type: {group_name}"
                                    }, status=status.HTTP_400_BAD_REQUEST)

                                model, field_name = VISIBILITY_MAP[group_name]

                                # Fetch all objects matching the IDs
                                objects = model.objects.filter(id__in=ids)

                                if objects.count() != len(ids):
                                    return Response({
                                        "error": f"Some IDs in {group_name} do not exist."
                                    }, status=status.HTTP_400_BAD_REQUEST)

                                # Add to the many-to-many field
                                getattr(visibility, field_name).add(*objects)

                                visibility.save()
                                new_visibility = copy.copy(visibility)

                                VisibilityLog.objects.create(
                                        event=visibility.event,
                                        old_visibility=old_visibility,
                                        new_visibility=new_visibility,
                                        changed_by=created_by
                                    )
                                visibility.save()
                        except EventVisibility.DoesNotExist:
                            pass
                    break
                time.sleep(1)
            except Exception:
                # fail silently for background checker
                return

        checker_thread = Thread(target=_schedule_checker, args=(visibility_id, expiry_time), daemon=True)
        checker_thread.start()

        return Response({
            "message": "Visibility items added successfully.",
            "added": visibility_groups
        }, status=status.HTTP_200_OK)

class VisibilityLogViewSet(ModelViewSet):
    serializer_class = VisibilityLogSerializer
    queryset = VisibilityLog.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]


class EventCategoryViewSet(ModelViewSet):
    serializer_class = EventCategorySerializer
    queryset = EventCategory.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventAttendanceViewSet(ModelViewSet):
    serializer_class = EventAttendanceSerializer
    queryset = EventAttendance.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventBudgetViewSet(ModelViewSet):
    serializer_class = EventBudgetSerializer
    queryset = EventBudget.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventCategoryAssignmentViewSet(ModelViewSet):
    serializer_class = EventCategoryAssignmentSerializer
    queryset = EventCategoryAssignment.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventFeedbackViewSet(ModelViewSet):
    serializer_class = EventFeedbackSerializer
    queryset = EventFeedback.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def rate(self, request, name=None):
        event = self.get_object()
        if not event.activate_feedback:
            return Response({'message': 'This event does not allow feedback.'}, status=status.HTTP_400_BAD_REQUEST)

        rating_value = request.data.get('rating')
        if rating_value and 1 <= int(rating_value) <= 5:
            rating, created = EventFeedback.objects.get_or_create(event=event, user=request.user)
            rating.rating = rating_value
            rating.save()
            return Response({'status': 'Event rated'}, status=status.HTTP_200_OK)
        return Response({'error': 'Rating value must be between 1 and 5'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def rating(self, request, name=None):
        event = self.get_object()
        if not event.viewable:
            return Response({'message': 'This event does not allow comments viewwing.'}, status=status.HTTP_400_BAD_REQUEST)
        
        ratings = EventFeedback.objects.filter(event=event)
        if ratings.exists():
            average_rating = ratings.aggregate(models.Avg('rating'))['rating__avg']
            return Response({'average_rating': average_rating}, status=status.HTTP_200_OK)
        return Response({'average_rating': 0}, status=status.HTTP_200_OK)

class EventFeedbackResponseViewSet(ModelViewSet):
    serializer_class = EventFeedbackResponseSerializer
    queryset = EventFeedbackResponse.objects.all()
    permission_classes = [IsModerator]

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def respond(self, request, name=None):
        serializer = EventFeedbackResponseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': f'Invalid data input. This is the error: {serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        event = serializer.save()

        attendance_status = serializer.validated_data['attendance_status']

        if attendance_status == 'blocked':
            try:
                user = request.user
                profile = Profile.objects.get(user=user)
                profile.blocked_events.add(event)
                profile.save()
                return Response({'status': 'Response submitted successfully'}, status=status.HTTP_200_OK)
            except Profile.DoesNotExist:
                return Response({'error': 'User invalid. You have not created a profile yet.'})
            
        # give the fedback below if the event was not blocked
        return Response({'status': 'Response submitted successfully'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def block_from_creator(self, request, name=None):
        feedback = self.get_object()
        event = feedback.event
        creator = event.created_by
        user = request.user
        profile = Profile.objects.get(user=user)
        events = Event.objects.filter(created_by=creator)
        profile.blocked_events.add(*events)
        profile.save()
        return Response({'status': 'Creator blocked successfully'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unblock_from_creator(self, request, name=None):
        feedback = self.get_object()
        event = feedback.event
        creator = event.created_by
        user = request.user
        profile = Profile.objects.get(user=user)
        events = Event.objects.filter(created_by=creator)
        profile.blocked_events.remove(*events)
        profile.save()
        return Response({'status': 'Creator unblocked successfully'}, status=status.HTTP_200_OK)

    # TODO: Implement sharing after dms and rooms are configured
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def share_event(self, request, name=None):
        '''Share event from feedback'''
        feedback = self.get_object()
        event = feedback.event
        platform = request.data.get('platform')
        link = request.data.get('link')
        # Implement sharing logic here (e.g., generate shareable link, integrate with social media APIs)
        # shareable_link = f"http://example.com/events/{event.id}/"
        return Response({'status': f'Event shared on {platform}', 'link': link}, status=status.HTTP_200_OK)
    



class EventLikeViewSet(ModelViewSet):
    serializer_class = EventLikeSerializer
    queryset = EventLike.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def comment(self, request, name=None):
        event = self.get_object()
        user = request.user
        comment_text = request.data.get('comment')
        if not event.activate_feedback:
            return Response({'message': 'This event does not allow feedback.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if comment_text:
            comment = EventLike.objects.create(event=event, user=user, comment=comment_text)
            comment.save()
            return Response({'status': 'Comment added'}, status=status.HTTP_200_OK)
        return Response({'error': 'Comment text is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def comments(self, request, name=None):
        event = self.get_object()

        if not event.viewable:
            return Response({'message': 'This event does not allow comments viewwing.'}, status=status.HTTP_400_BAD_REQUEST)
        comments = EventLike.objects.filter(event=event).order_by('-created_on')
        serializer = EventLikeSerializer(comments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def like(self, request, name=None):
        event = self.get_object()
        user = request.user

        if not event.activate_feedback:
            return Response({'message': 'This event does not allow feedback.'}, status=status.HTTP_400_BAD_REQUEST)

        if not event:
            return Response({'error': 'No event was parsed from the frontend.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        event = EventLike.objects.filter(event=event, user=user)
        if not event:
            event = EventLike.objects.create(event=event, user=user)
        
        event.like = True
        event.save()
        return Response({'status': 'Event liked'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unlike(self, request, name=None):
        event = self.get_object()
        user = request.user
        
        if not event.activate_feedback:
            return Response({'message': 'This event does not allow feedback.'}, status=status.HTTP_400_BAD_REQUEST)

        if not event:
            return Response({'error': 'No event was parsed from the frontend.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        event = EventLike.objects.filter(event=event, user=user)
        if not event:
            event = EventLike.objects.create(event=event, user=user)
        
        event.unlike = True
        event.save()
        return Response({'status': 'Event unliked'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def likes(self, request, name=None):
        event = self.get_object()

        if not event.viewable:
            return Response({'message': 'This event does not allow comments viewwing.'}, status=status.HTTP_400_BAD_REQUEST)
        
        likes_count = event.likes.count()
        return Response({'likes_count': likes_count}, status=status.HTTP_200_OK)

class EventCollaborationViewSet(ModelViewSet):
    serializer_class = EventCollaborationSerializer
    queryset = EventCollaboration.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventFileViewSet(ModelViewSet):
    serializer_class = EventFileSerializer
    queryset = EventFile.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]


class EventInvitationViewSet(ModelViewSet):
    serializer_class = EventInvitationSerializer
    queryset = EventInvitation.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventMediaCoverageViewSet(ModelViewSet):
    serializer_class = EventMediaCoverageSerializer
    queryset = EventMediaCoverage.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventFollowUpViewSet(ModelViewSet):
    serializer_class = EventFollowUpSerializer
    queryset = EventFollowUp.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventLogisticsViewSet(ModelViewSet):
    serializer_class = EventLogisticsSerializer
    queryset = EventLogistics.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventPartnershipViewSet(ModelViewSet):
    serializer_class = EventPartnershipSerializer
    queryset = EventPartnership.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventPhotoViewSet(ModelViewSet):
    serializer_class = EventPhotoSerializer
    queryset = EventPhoto.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventPromotionViewSet(ModelViewSet):
    serializer_class = EventPromotionSerializer
    queryset = EventPromotion.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventRegistrationViewSet(ModelViewSet):
    serializer_class = EventRegistrationSerializer
    queryset = EventRegistration.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]


    @action(detail=True, methods=['post'])
    def book_slot(self, request, name=None):
        event = self.get_object()
        serializer = EventRegistrationSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': f'Invalid data input. This is the error: {serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()
        return Response({'status': 'You booked a slot successfully'}, status=status.HTTP_200_OK)

class EventReminderViewSet(ModelViewSet):
    serializer_class = EventReminderSerializer
    queryset = EventReminder.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventReportViewSet(ModelViewSet):
    serializer_class = EventReportSerializer
    queryset = EventReport.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSpeakerViewSet(ModelViewSet):
    serializer_class = EventSpeakerSerializer
    queryset = EventSpeaker.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventScheduleViewSet(ModelViewSet):
    serializer_class = EventScheduleSerializer
    queryset = EventSchedule.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSessionViewSet(ModelViewSet):
    serializer_class = EventSessionSerializer
    queryset = EventSession.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorViewSet(ModelViewSet):
    serializer_class = EventSponsorSerializer
    queryset = EventSponsor.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorAgreementViewSet(ModelViewSet):
    serializer_class = EventSponsorAgreementSerializer
    queryset = EventSponsorAgreement.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorBenefitViewSet(ModelViewSet):
    serializer_class = EventSponsorBenefitSerializer
    queryset = EventSponsorBenefit.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorPaymentViewSet(ModelViewSet):
    serializer_class = EventSponsorPaymentSerializer
    queryset = EventSponsorPayment.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorLogoViewSet(ModelViewSet):
    serializer_class = EventSponsorLogoSerializer
    queryset = EventSponsorLogo.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorPackageViewSet(ModelViewSet):
    serializer_class = EventSponsorPackageSerializer
    queryset = EventSponsorPackage.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorshipAgreementDocumentViewSet(ModelViewSet):
    serializer_class = EventSponsorshipAgreementDocumentSerializer
    queryset = EventSponsorshipAgreementDocument.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorshipApprovalViewSet(ModelViewSet):
    serializer_class = EventSponsorshipApprovalSerializer
    queryset = EventSponsorshipApproval.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorshipApplicationViewSet(ModelViewSet):
    serializer_class = EventSponsorshipApplicationSerializer
    queryset = EventSponsorshipApplication.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorshipCertificateViewSet(ModelViewSet):
    serializer_class = EventSponsorshipCertificateSerializer
    queryset = EventSponsorshipCertificate.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorshipContractViewSet(ModelViewSet):
    serializer_class = EventSponsorshipContractSerializer
    queryset = EventSponsorshipContract.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorshipDowngradeViewSet(ModelViewSet):
    serializer_class = EventSponsorshipDowngradeSerializer
    queryset = EventSponsorshipDowngrade.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorshipEvaluationViewSet(ModelViewSet):
    serializer_class = EventSponsorshipEvaluationSerializer
    queryset = EventSponsorshipEvaluation.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorshipExtensionViewSet(ModelViewSet):
    serializer_class = EventSponsorshipExtensionSerializer
    queryset = EventSponsorshipExtension.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorshipFeedbackViewSet(ModelViewSet):
    serializer_class = EventSponsorshipFeedbackSerializer
    queryset = EventSponsorshipFeedback.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorshipHistoryViewSet(ModelViewSet):
    serializer_class = EventSponsorshipHistorySerializer
    queryset = EventSponsorshipHistory.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorshipInvoiceViewSet(ModelViewSet):
    serializer_class = EventSponsorshipInvoiceSerializer
    queryset = EventSponsorshipInvoice.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorshipLetterViewSet(ModelViewSet):
    serializer_class = EventSponsorshipLetterSerializer
    queryset = EventSponsorshipLetter.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorshipLevelViewSet(ModelViewSet):
    serializer_class = EventSponsorshipLevelSerializer
    queryset = EventSponsorshipLevel.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorshipRecognitionViewSet(ModelViewSet):
    serializer_class = EventSponsorshipRecognitionSerializer
    queryset = EventSponsorshipRecognition.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorshipRejectionViewSet(ModelViewSet):
    serializer_class = EventSponsorshipRejectionSerializer
    queryset = EventSponsorshipRejection.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorshipRenewalViewSet(ModelViewSet):
    serializer_class = EventSponsorshipRenewalSerializer
    queryset = EventSponsorshipRenewal.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorshipRenewalViewSet(ModelViewSet):
    serializer_class = EventSponsorshipRenewalSerializer
    queryset = EventSponsorshipRenewal.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorshipReportViewSet(ModelViewSet):
    serializer_class = EventSponsorshipReportSerializer
    queryset = EventSponsorshipReport.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorshipTerminationViewSet(ModelViewSet):
    serializer_class = EventSponsorshipTerminationSerializer
    queryset = EventSponsorshipTermination.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorshipTransferViewSet(ModelViewSet):
    serializer_class = EventSponsorshipTransferSerializer
    queryset = EventSponsorshipTransfer.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSponsorshipUpgradeViewSet(ModelViewSet):
    serializer_class = EventSponsorshipUpgradeSerializer
    queryset = EventSponsorshipUpgrade.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSurveyViewSet(ModelViewSet):
    serializer_class = EventSurveySerializer
    queryset = EventSurvey.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSurveyQuestionViewSet(ModelViewSet):
    serializer_class = EventSurveyQuestionSerializer
    queryset = EventSurveyQuestion.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventSurveyResponseViewSet(ModelViewSet):
    serializer_class = EventSurveyResponseSerializer
    queryset = EventSurveyResponse.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventTagViewSet(ModelViewSet):
    serializer_class = EventTagSerializer
    queryset = EventTag.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventTagAssignmentViewSet(ModelViewSet):
    serializer_class = EventTagAssignmentSerializer
    queryset = EventTagAssignment.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventTicketViewSet(ModelViewSet):
    serializer_class = EventTicketSerializer
    queryset = EventTicket.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventVideoViewSet(ModelViewSet):
    serializer_class = EventVideoSerializer
    queryset = EventVideo.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]


class EventSlotBookingViewSet(ModelViewSet):
    """ViewSet for slot bookings with booking, availability and cancellation"""
    serializer_class = EventSlotBookingSerializer
    queryset = EventSlotBooking.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_fields = ['event', 'user', 'booking_status']

    @action(detail=False, methods=['post'])
    def book_slot(self, request):
        """Book a slot for an event. Auto-generates ticket if capacity available. Supports bulk."""
        event_id = request.data.get('event_id')
        tickets_data = request.data.get('tickets_data', [])

        # Fallback for old single ticket flow
        if not tickets_data:
            ticket_id = request.data.get('ticket_id')
            ticket_tier_id = request.data.get('ticket_tier_id')
            quantity = int(request.data.get('quantity', 1))
            if ticket_id or ticket_tier_id or quantity > 0:
                tickets_data = [{'ticket_id': ticket_id, 'ticket_tier_id': ticket_tier_id, 'quantity': quantity}]
        
        if not tickets_data:
            return Response({'error': 'No tickets selected for purchase'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)

        # Optional Profile Fetch for age validation
        user_profile = getattr(request.user, 'profile', None)
        user_age = None
        if user_profile and user_profile.date_of_birth:
            today = datetime.today()
            dob = user_profile.date_of_birth
            user_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        
        # Check overall capacity
        confirmed = event.slot_bookings.filter(booking_status__in=['confirmed', 'checked_in']).aggregate(
            total=models.Sum('quantity')
        )['total'] or 0
        
        total_quantity_requested = sum([int(t.get('quantity', 1)) for t in tickets_data])
        if confirmed + total_quantity_requested > event.capacity:
            return Response({'error': f'Event capacity exceeded. Only {event.capacity - confirmed} slots left.'}, status=status.HTTP_400_BAD_REQUEST)

        bookings_created = []
        is_free_batch = True

        for item in tickets_data:
            ticket_id = item.get('ticket_id')
            ticket_tier_id = item.get('ticket_tier_id')
            quantity = int(item.get('quantity', 1))

            if quantity < 1:
                continue

            ticket = None
            tier = None
            amount = 0.00
            is_free = True

            # if it's sending ticket_id but the model expects ticket tiers to be fetched by that ID because of frontend mixup:
            # Let's try matching TicketTier first if we think it came from the new UI
            if ticket_id and not ticket_tier_id:
                try:
                    tier = TicketTier.objects.get(pk=ticket_id, event=event)
                    ticket_tier_id = tier.id
                    ticket_id = None
                except TicketTier.DoesNotExist:
                    pass

            if ticket_tier_id:
                try:
                    tier = TicketTier.objects.get(pk=ticket_tier_id, event=event)
                    if tier.min_age and (user_age is None or user_age < tier.min_age):
                        return Response({'error': f'You must be at least {tier.min_age} to buy {tier.name}.'}, status=status.HTTP_403_FORBIDDEN)
                    if tier.max_age and (user_age is None or user_age > tier.max_age):
                        return Response({'error': f'You must be under {tier.max_age} to buy {tier.name}.'}, status=status.HTTP_403_FORBIDDEN)
                    
                    tier_booked = EventSlotBooking.objects.filter(ticket_tier=tier, booking_status__in=['confirmed', 'checked_in']).aggregate(
                        total=models.Sum('quantity')
                    )['total'] or 0
                    if tier_booked + quantity > tier.capacity:
                        return Response({'error': f'Tier "{tier.name}" capacity exceeded.'}, status=status.HTTP_400_BAD_REQUEST)
                    
                    amount = float(tier.price) * quantity
                    is_free = (float(tier.price) == 0.00)
                except TicketTier.DoesNotExist:
                    return Response({'error': 'Ticket Tier not found'}, status=status.HTTP_404_NOT_FOUND)
                
            elif ticket_id:
                try:
                    ticket = EventTicket.objects.get(pk=ticket_id, event=event)
                    amount = float(ticket.price) * quantity
                    is_free = ticket.is_free
                except EventTicket.DoesNotExist:
                    return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)
            else:
                ticket = event.tickets.first()
                if not ticket:
                    ticket = EventTicket.objects.create(
                        event=event, ticket_type='regular', price=0.00,
                        quantity_available=event.capacity, is_free=True
                    )
                amount = 0 if ticket.is_free else float(ticket.price) * quantity
                is_free = ticket.is_free

            if not tier:
                existing = EventSlotBooking.objects.filter(event=event, user=request.user).first()
                if existing and len(tickets_data) == 1:
                    return Response({'error': 'You have already booked a slot for this event', 'booking': EventSlotBookingSerializer(existing).data}, status=status.HTTP_400_BAD_REQUEST)

            if not is_free:
                is_free_batch = False

            booking = EventSlotBooking.objects.create(
                event=event,
                user=request.user,
                ticket=ticket,
                ticket_tier=tier,
                quantity=quantity,
                booking_status='confirmed' if is_free else 'pending',
                amount_paid=amount
            )
            bookings_created.append(booking)

        # Analytics Logging
        EventInteractionAnalytics.objects.create(
            event=event, user=request.user, interaction_type='ticket_click',
            viewer_age=user_age
        )

        serializer = EventSlotBookingSerializer(bookings_created, many=True)
        return Response({
            'message': 'Slots booked successfully!' if is_free_batch else 'Booking created. Please complete payment.',
            'purchases': serializer.data,
            'is_free': is_free_batch,
            'quantity': total_quantity_requested,
            'requires_payment': not is_free_batch
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def my_bookings(self, request):
        """Get all bookings for the current user"""
        bookings = EventSlotBooking.objects.filter(user=request.user).order_by('-booked_at')
        serializer = EventSlotBookingSerializer(bookings, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='availability/(?P<event_id>[^/.]+)')
    def availability(self, request, event_id=None):
        """Get slot availability for an event including new tier structures"""
        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)

        confirmed = event.slot_bookings.filter(booking_status__in=['confirmed', 'checked_in']).aggregate(
            total=models.Sum('quantity')
        )['total'] or 0
        remaining = max(0, event.capacity - confirmed)
        tickets = event.tickets.all()
        tiers = event.ticket_tiers.filter(is_active=True)

        return Response({
            'event_id': event.id,
            'event_name': event.name,
            'capacity': event.capacity,
            'booked': confirmed,
            'slots_remaining': remaining,
            'is_full': remaining == 0,
            'tickets': [{
                'id': t.id,
                'type': t.ticket_type,
                'price': str(t.price),
                'is_free': t.is_free,
                'quantity_available': t.quantity_available,
            } for t in tickets],
            'tiers': [{
                'id': tier.id,
                'name': tier.name,
                'price': str(tier.price),
                'capacity': tier.capacity,
                'group_size': tier.group_size,
                'description': tier.description,
                'min_age': tier.min_age,
                'max_age': tier.max_age
            } for tier in tiers]
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a booking"""
        booking = self.get_object()
        if booking.user != request.user:
            return Response({'error': 'You can only cancel your own bookings'}, status=status.HTTP_403_FORBIDDEN)
        booking.booking_status = 'cancelled'
        booking.save()
        return Response({'message': 'Booking cancelled successfully'})

    @action(detail=True, methods=['post'])
    def confirm_payment(self, request, pk=None):
        """Confirm payment for a paid booking"""
        booking = self.get_object()
        if booking.user != request.user:
            return Response({'error': 'You can only confirm your own bookings'}, status=status.HTTP_403_FORBIDDEN)
        booking.booking_status = 'confirmed'
        booking.save()
        serializer = EventSlotBookingSerializer(booking)
        return Response({
            'message': 'Payment confirmed. Your ticket is ready!',
            'booking': serializer.data
        })


class EventInteractionAnalyticsViewSet(ModelViewSet):
    """ViewSet to handle granular interaction logging (post) and analytics dashboard retrieval (get)"""
    serializer_class = EventInteractionAnalyticsSerializer
    queryset = EventInteractionAnalytics.objects.all()
    # Log interactions from any authenticated user, view stats via dedicated queries
    permission_classes = [IsAuthenticated] 

    @action(detail=False, methods=['post'])
    def log_interaction(self, request):
        event_id = request.data.get('event_id')
        interaction_type = request.data.get('interaction_type')
        duration = int(request.data.get('duration_seconds', 0))

        if not event_id or not interaction_type:
            return Response({'error': 'event_id and interaction_type are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)

        # Basic cached demographics extraction
        user_profile = getattr(request.user, 'profile', None)
        user_age = None
        if user_profile and user_profile.date_of_birth:
            today = datetime.today()
            dob = user_profile.date_of_birth
            user_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        EventInteractionAnalytics.objects.create(
            event=event,
            user=request.user,
            interaction_type=interaction_type,
            duration_seconds=duration,
            viewer_age=user_age,
            # (Country and City could be extracted here from user Profile/Account settings if implemented)
        )
        return Response({'status': 'logged'}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def event_dashboard(self, request):
        """Retrieve aggregated statistics for the event created by the current user"""
        event_id = request.query_params.get('event_id')
        if not event_id:
            return Response({'error': 'event_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Only allow the creator/admins to view stats
        if event.created_by != request.user and not request.user.is_staff:
            return Response({'error': 'Not authorized to view stats for this event'}, status=status.HTTP_403_FORBIDDEN)

        interactions = EventInteractionAnalytics.objects.filter(event=event)
        
        # Aggregate Views, Shares, etc.
        total_views = interactions.filter(interaction_type='view').count()
        total_shares = interactions.filter(interaction_type='share').count()
        ticket_clicks = interactions.filter(interaction_type='ticket_click').count()

        # Ticket Sales Velocity (mocking simple counts for now)
        ticket_sales = event.slot_bookings.filter(booking_status__in=['confirmed', 'checked_in']).count()
        
        # Simple Age clusters
        age_distribution = {
            'Under 18': interactions.filter(viewer_age__lt=18).count(),
            '18-24': interactions.filter(viewer_age__gte=18, viewer_age__lte=24).count(),
            '25-34': interactions.filter(viewer_age__gte=25, viewer_age__lte=34).count(),
            '35+': interactions.filter(viewer_age__gte=35).count(),
            'Unknown': interactions.filter(viewer_age__isnull=True).count(),
        }

        return Response({
            'total_views': total_views,
            'total_shares': total_shares,
            'engagement_clicks': ticket_clicks,
            'tickets_sold': ticket_sales,
            'age_distribution': age_distribution
        })
