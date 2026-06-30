from django.shortcuts import render
from django.http import HttpResponse
from django.db import models, IntegrityError
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import TruncMonth
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ModelViewSet
from Events.serializers import EventSerializer
from Events.models import Event, EventCategory, EventAttendance, EventBudget, EventCategoryAssignment, EventCollaboration, EventFeedback, EventFeedbackResponse, EventFile, EventFollowUp, EventLogistics, EventMediaCoverage, EventPartnership, EventPhoto, EventPromotion, EventRegistration, EventReminder, EventSchedule, EventSession, EventSpeaker, EventSponsor, EventSponsorAgreement, EventSponsorBenefit, EventSponsorLogo, EventSponsorPackage, EventSponsorPayment, EventSponsorshipAgreementDocument, EventSponsorshipApplication, EventSponsorshipApproval, EventSponsorshipCertificate, EventSponsorshipContract, EventSponsorshipDowngrade, EventSponsorshipEvaluation, EventSponsorshipExtension, EventSponsorshipFeedback, EventSponsorshipHistory, EventSponsorshipInvoice, EventSponsorshipLetter, EventSponsorshipLevel, EventSponsorshipRecognition, EventSponsorshipRejection, EventSponsorshipRenewal, EventSponsorshipReport, EventSponsorshipTermination, EventSponsorshipTransfer, EventSponsorshipUpgrade, EventSurvey, EventSurveyQuestion, EventSurveyResponse, EventSurveyTemplate, EventTag, EventTagAssignment, EventTicket, EventVideo, EventReport, EventInvitation, EventLike, EventVisibility, VisibilityLog, EventSlotBooking, TicketTier, EventInteractionAnalytics, EventMaterial, OrganizerProfile, SponsorProfile, OrganizerFollow, SponsorFollow, PartnershipInvitation, CoOrganizer, SponsorApplication, SponsorshipNegotiation
from Events.serializers import EventSerializer, EventCategorySerializer, EventAttendanceSerializer, EventBudgetSerializer, EventCategoryAssignmentSerializer, EventCollaborationSerializer, EventFeedbackSerializer, EventFeedbackResponseSerializer, EventFileSerializer, EventFollowUpSerializer, EventLogisticsSerializer, EventMediaCoverageSerializer, EventPartnershipSerializer, EventPhotoSerializer, EventPromotionSerializer, EventRegistrationSerializer, EventReminderSerializer, EventScheduleSerializer, EventSessionSerializer, EventSpeakerSerializer, EventSponsorSerializer, EventSponsorAgreementSerializer, EventSponsorBenefitSerializer, EventSponsorLogoSerializer, EventSponsorPackageSerializer, EventSponsorPaymentSerializer, EventSponsorshipAgreementDocumentSerializer, EventSponsorshipApplicationSerializer, EventSponsorshipApprovalSerializer, EventSponsorshipCertificateSerializer, EventSponsorshipContractSerializer, EventSponsorshipDowngradeSerializer, EventSponsorshipEvaluationSerializer, EventSponsorshipExtensionSerializer, EventSponsorshipFeedbackSerializer, EventSponsorshipHistorySerializer, EventSponsorshipInvoiceSerializer, EventSponsorshipLetterSerializer, EventSponsorshipLevelSerializer, EventSponsorshipRecognitionSerializer, EventSponsorshipRejectionSerializer, EventSponsorshipRenewalSerializer, EventSponsorshipReportSerializer, EventSponsorshipTerminationSerializer, EventSponsorshipTransferSerializer, EventSponsorshipUpgradeSerializer, EventSurveySerializer, EventSurveyQuestionSerializer, EventSurveyResponseSerializer, EventSurveyTemplateSerializer, EventTagSerializer, EventTagAssignmentSerializer, EventTicketSerializer, EventVideoSerializer, EventReportSerializer, EventInvitationSerializer, EventLikeSerializer, EventVisibilitySerializer, VisibilityLogSerializer, EventSlotBookingSerializer, EventInteractionAnalyticsSerializer, OrganizerProfileSerializer, SponsorProfileSerializer, OrganizerFollowSerializer, SponsorFollowSerializer, PartnershipInvitationSerializer, CoOrganizerSerializer, SponsorApplicationSerializer, SponsorshipNegotiationSerializer
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
                    category=tier_data.get('category', 'individual'),
                    tier=tier_data.get('tier', 'regular'),
                    price=tier_data.get('price', 0.00),
                    capacity=tier_data.get('capacity', 0),
                    min_age=tier_data.get('min_age'),
                    max_age=tier_data.get('max_age'),
                    custom_criteria=tier_data.get('custom_criteria', ''),
                    group_size=tier_data.get('group_size', 1),
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

        # Process Categories
        categories_data = request_data.get('categories', [])
        if isinstance(categories_data, str):
            try:
                categories_data = json.loads(categories_data)
            except json.JSONDecodeError:
                categories_data = []
        if categories_data:
            EventCategoryAssignment.objects.filter(event=event).delete()
            for cat_id in categories_data:
                try:
                    cat = EventCategory.objects.get(pk=int(cat_id))
                    EventCategoryAssignment.objects.create(event=event, category=cat)
                except (EventCategory.DoesNotExist, ValueError):
                    continue

        # Process Sponsorship Levels
        sponsorship_levels_data = request_data.get('sponsorship_levels', [])
        if isinstance(sponsorship_levels_data, str):
            try:
                sponsorship_levels_data = json.loads(sponsorship_levels_data)
            except json.JSONDecodeError:
                sponsorship_levels_data = []
        if sponsorship_levels_data:
            EventSponsorshipLevel.objects.filter(event=event).delete()
            for level_data in sponsorship_levels_data:
                EventSponsorshipLevel.objects.create(
                    event=event,
                    level_name=level_data.get('level_name', ''),
                    level_benefits=level_data.get('level_benefits', ''),
                    level_price=level_data.get('level_price', 0),
                )


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
        
        if not instance.event_organizer:
            org_profile = OrganizerProfile.objects.filter(user=self.request.user).first()
            if org_profile:
                instance.event_organizer = org_profile
                instance.save(update_fields=['event_organizer'])
        
        if not instance.organisation_id:
            from Organisation.models import OrganisationMember
            membership = OrganisationMember.objects.filter(
                user=self.request.user, is_active=True
            ).select_related('organisation').first()
            if membership:
                instance.organisation = membership.organisation
                instance.save(update_fields=['organisation'])
        
        # Auto-create Event Kitty (PaymentGroup)
        try:
            from Payment.models import PaymentGroups
            from django.contrib.contenttypes.models import ContentType
            
            content_type = ContentType.objects.get_for_model(instance)
            group_name = instance.event_organizer.business_name if instance.event_organizer else f"Event Kitty - {instance.name}"
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
    
    @action(detail=True, methods=['post'])
    def duplicate_event(self, request, name=None):
        """Duplicate event by copying the original"""
        original = self.get_object()
        original_data = EventSerializer(original).data
        original_data.pop('id', None)
        original_data.pop('uuid', None)
        original_data['name'] = f"{original.name} (Copy)"
        original_data['status'] = 'draft'
        serializer = EventSerializer(data=original_data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user)
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
            return Response({'error': f'Invalid data input.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()

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

class OrganizerDashboardViewSet(ModelViewSet):
    queryset = OrganizerProfile.objects.none()
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        try:
            organizer = OrganizerProfile.objects.get(user=request.user)
        except OrganizerProfile.DoesNotExist:
            return Response({'error': 'Organizer profile not found'}, status=404)

        events = Event.objects.filter(event_organizer=organizer)

        total_events = events.count()

        total_attendees = EventRegistration.objects.filter(
            event__in=events,
            attendance_permission='approved'
        ).values('user').distinct().count()

        revenue_agg = EventSlotBooking.objects.filter(
            event__in=events,
            booking_status__in=['confirmed', 'checked_in']
        ).aggregate(total=Sum('amount_paid'))
        total_revenue = float(revenue_agg['total'] or 0)

        sponsor_agg = EventSponsor.objects.filter(
            event__in=events
        ).aggregate(total=Sum('contribution_amount'))
        total_sponsorship = float(sponsor_agg['total'] or 0)

        rating_agg = EventFeedback.objects.filter(
            event__in=events
        ).aggregate(avg=Avg('rating'))
        avg_rating = round(float(rating_agg['avg']), 2) if rating_agg['avg'] else None

        total_views = EventInteractionAnalytics.objects.filter(
            event__in=events,
            interaction_type='view'
        ).count()

        total_bookings = EventRegistration.objects.filter(
            event__in=events,
            attendance_permission='approved'
        ).count()

        event_metrics = []
        for event in events:
            sold_agg = EventSlotBooking.objects.filter(
                event=event,
                booking_status__in=['confirmed', 'checked_in']
            ).aggregate(total=Sum('quantity'))
            tickets_sold = sold_agg['total'] or 0

            rev_agg = EventSlotBooking.objects.filter(
                event=event,
                booking_status__in=['confirmed', 'checked_in']
            ).aggregate(total=Sum('amount_paid'))
            revenue = float(rev_agg['total'] or 0)

            interested_count = EventRegistration.objects.filter(event=event).count()
            booked_count = EventRegistration.objects.filter(event=event, attendance_permission='approved').count()
            checked_in_count = EventAttendance.objects.filter(event=event).count()

            views = EventInteractionAnalytics.objects.filter(
                event=event,
                interaction_type='view'
            ).count()

            event_metrics.append({
                'id': event.id,
                'name': event.name,
                'event_date': event.event_date,
                'status': event.status,
                'tickets_sold': tickets_sold,
                'revenue': revenue,
                'interested_count': interested_count,
                'booked_count': booked_count,
                'checked_in_count': checked_in_count,
                'views': views,
            })

        conversion_funnel = []
        for event in events:
            views = EventInteractionAnalytics.objects.filter(
                event=event,
                interaction_type='view'
            ).count()
            interested = EventRegistration.objects.filter(event=event).count()
            booked = EventRegistration.objects.filter(event=event, attendance_permission='approved').count()
            checked_in = EventAttendance.objects.filter(event=event).count()

            conversion_funnel.append({
                'event_id': event.id,
                'event_name': event.name,
                'views': views,
                'interested': interested,
                'booked': booked,
                'checked_in': checked_in,
            })

        category_data = []
        for cat_val, cat_label in [('individual', 'Individual'), ('couple', 'Couple'), ('group', 'Group')]:
            tier_ids = TicketTier.objects.filter(event__in=events, category=cat_val).values_list('id', flat=True)
            bookings = EventSlotBooking.objects.filter(
                ticket_tier_id__in=list(tier_ids),
                booking_status__in=['confirmed', 'checked_in']
            )
            cat_sales = bookings.aggregate(total=Sum('quantity'))['total'] or 0
            cat_revenue = float(bookings.aggregate(total=Sum('amount_paid'))['total'] or 0)
            category_data.append({
                'category': cat_val,
                'label': cat_label,
                'sales': cat_sales,
                'revenue': cat_revenue,
            })

        tier_performance = []
        for tier in TicketTier.objects.filter(event__in=events):
            sold = EventSlotBooking.objects.filter(
                ticket_tier=tier,
                booking_status__in=['confirmed', 'checked_in']
            ).aggregate(total=Sum('quantity'))['total'] or 0
            tier_rev = float(EventSlotBooking.objects.filter(
                ticket_tier=tier,
                booking_status__in=['confirmed', 'checked_in']
            ).aggregate(total=Sum('amount_paid'))['total'] or 0)
            tier_performance.append({
                'id': tier.id,
                'name': tier.name,
                'category': tier.category,
                'tier': tier.tier,
                'price': float(tier.price),
                'capacity': tier.capacity,
                'sold': sold,
                'revenue': tier_rev,
                'event_id': tier.event_id,
                'event_name': tier.event.name,
            })

        net_revenue = total_revenue + total_sponsorship

        year_filter = request.query_params.get('year')
        revenue_qs = EventSlotBooking.objects.filter(
            event__in=events,
            booking_status__in=['confirmed', 'checked_in']
        )
        if year_filter:
            revenue_qs = revenue_qs.filter(booked_at__year=year_filter)
        revenue_timeline = (
            revenue_qs
            .annotate(month=TruncMonth('booked_at'))
            .values('month')
            .annotate(revenue=Sum('amount_paid'))
            .order_by('month')
        )
        revenue_timeline_data = [
            {
                'month': item['month'].strftime('%Y-%m') if item['month'] else None,
                'revenue': float(item['revenue'])
            }
            for item in revenue_timeline
        ]

        return Response({
            'overview': {
                'total_events': total_events,
                'total_attendees': total_attendees,
                'total_revenue': total_revenue,
                'total_sponsorship': total_sponsorship,
                'avg_rating': avg_rating,
                'total_views': total_views,
                'total_bookings': total_bookings,
            },
            'events': event_metrics,
            'conversion_funnel': conversion_funnel,
            'ticket_categories': category_data,
            'tier_performance': tier_performance,
            'financial_summary': {
                'total_revenue': total_revenue,
                'total_sponsorship': total_sponsorship,
                'net_revenue': net_revenue,
            },
            'revenue_timeline': revenue_timeline_data,
        })

    @action(detail=False, methods=['get'])
    def demographics(self, request):
        try:
            organizer = OrganizerProfile.objects.get(user=request.user)
        except OrganizerProfile.DoesNotExist:
            return Response({'error': 'Organizer profile not found'}, status=404)

        events = Event.objects.filter(event_organizer=organizer)
        event_ids = events.values_list('id', flat=True)

        attendance = EventAttendance.objects.filter(event__in=events)

        gender_distribution = (
            attendance.values('gender')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        gender_data = [
            {'gender': item['gender'] or 'unknown', 'count': item['count']}
            for item in gender_distribution
        ]

        location_data = (
            attendance.values('location')
            .annotate(count=Count('id'))
            .order_by('-count')[:20]
        )
        location_data_list = [
            {'location': item['location'] or 'unknown', 'count': item['count']}
            for item in location_data
        ]

        category_data_demo = (
            attendance.values('category')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        category_data_list = [
            {'category': item['category'] or 'uncategorized', 'count': item['count']}
            for item in category_data_demo
        ]

        monthly_attendance = (
            attendance
            .annotate(month=TruncMonth('check_in_time'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )
        monthly_attendance_data = [
            {
                'month': item['month'].strftime('%Y-%m') if item['month'] else None,
                'count': item['count']
            }
            for item in monthly_attendance
        ]

        bookings_qs = EventSlotBooking.objects.filter(
            event__in=events,
            booking_status__in=['confirmed', 'checked_in']
        )

        monthly_revenue = (
            bookings_qs
            .annotate(month=TruncMonth('booked_at'))
            .values('month')
            .annotate(revenue=Sum('amount_paid'))
            .order_by('month')
        )
        monthly_revenue_data = [
            {
                'month': item['month'].strftime('%Y-%m') if item['month'] else None,
                'revenue': float(item['revenue'])
            }
            for item in monthly_revenue
        ]

        category_revenue = []
        for cat_val, cat_label in [('individual', 'Individual'), ('couple', 'Couple'), ('group', 'Group')]:
            tier_ids = TicketTier.objects.filter(event__in=events, category=cat_val).values_list('id', flat=True)
            rev = bookings_qs.filter(ticket_tier_id__in=list(tier_ids)).aggregate(total=Sum('amount_paid'))
            category_revenue.append({
                'category': cat_val,
                'label': cat_label,
                'revenue': float(rev['total'] or 0)
            })

        sponsorship_revenue = float(
            EventSponsor.objects.filter(event__in=events)
            .aggregate(total=Sum('contribution_amount'))['total'] or 0
        )

        return Response({
            'gender': gender_data,
            'location': location_data_list,
            'category': category_data_list,
            'monthly_attendance': monthly_attendance_data,
            'monthly_revenue': monthly_revenue_data,
            'category_revenue': category_revenue,
            'sponsorship_revenue': sponsorship_revenue,
        })

class OrganizerProfileViewSet(ModelViewSet):
    serializer_class = OrganizerProfileSerializer
    queryset = OrganizerProfile.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        self.request.user.is_organizer = True
        self.request.user.save(update_fields=['is_organizer'])

    @action(detail=False, methods=['get', 'patch'])
    def my_profile(self, request):
        profile = OrganizerProfile.objects.filter(user=request.user).first()
        if not profile:
            return Response({'error': 'No organizer profile found'}, status=404)
        if request.method == 'PATCH':
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def discover(self, request):
        from django.db.models import Count, Q
        qs = OrganizerProfile.objects.annotate(follower_count=Count('followers'))
        search = request.query_params.get('search', '')
        if search:
            qs = qs.filter(
                Q(business_name__icontains=search) |
                Q(location__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search)
            )
        partnership = request.query_params.get('partnership')
        if partnership == 'open':
            qs = qs.filter(is_open_for_partnership=True)
        page = self.paginate_queryset(qs)
        serializer_context = self.get_serializer_context()
        if request.user.is_authenticated:
            user_follows = OrganizerFollow.objects.filter(follower=request.user)
            follow_map = {f.organizer_id: f for f in user_follows}
        else:
            follow_map = {}
        if page is not None:
            serializer = self.get_serializer(page, many=True, context=serializer_context)
            data = serializer.data
            for item in data:
                org_id = item.get('id')
                follow = follow_map.get(org_id)
                item['is_following'] = follow is not None
                item['follow_id'] = follow.pk if follow else None
                item['notifications_enabled'] = follow.notifications_enabled if follow else None
            return self.get_paginated_response(data)
        serializer = self.get_serializer(qs, many=True, context=serializer_context)
        data = serializer.data
        for item in data:
            org_id = item.get('id')
            follow = follow_map.get(org_id)
            item['is_following'] = follow is not None
            item['follow_id'] = follow.pk if follow else None
            item['notifications_enabled'] = follow.notifications_enabled if follow else None
        return Response(data)

    @action(detail=True, methods=['post'])
    def follow(self, request, pk=None):
        profile = self.get_object()
        follow, created = OrganizerFollow.objects.get_or_create(
            follower=request.user,
            organizer=profile
        )
        if not created:
            follow.delete()
            return Response({'following': False})
        return Response({
            'following': True,
            'follow_id': follow.id,
            'notifications_enabled': follow.notifications_enabled,
        })

    @action(detail=False, methods=['get'])
    def following_events(self, request):
        followed_orgs = OrganizerFollow.objects.filter(
            follower=request.user
        ).values_list('organizer', flat=True)
        events = Event.objects.filter(
            Q(event_organizer_id__in=followed_orgs) & 
            (Q(seeking_partners=True) | Q(seeking_sponsors=True))
        )
        from Events.enhanced_serializers import EventDetailSerializer
        page = self.paginate_queryset(events)
        if page is not None:
            serializer = EventDetailSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = EventDetailSerializer(events, many=True, context={'request': request})
        return Response(serializer.data)

class SponsorProfileViewSet(ModelViewSet):
    serializer_class = SponsorProfileSerializer
    queryset = SponsorProfile.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        self.request.user.is_sponsor = True
        self.request.user.save(update_fields=['is_sponsor'])

    @action(detail=False, methods=['get', 'patch'])
    def my_profile(self, request):
        profile = SponsorProfile.objects.filter(user=request.user).first()
        if not profile:
            return Response({'error': 'No sponsor profile found'}, status=404)
        if request.method == 'PATCH':
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def discover(self, request):
        from django.db.models import Count, Q
        qs = SponsorProfile.objects.annotate(follower_count=Count('followers'))
        search = request.query_params.get('search', '')
        if search:
            qs = qs.filter(
                Q(company_name__icontains=search) |
                Q(industry__icontains=search) |
                Q(location__icontains=search)
            )
        page = self.paginate_queryset(qs)
        serializer_context = self.get_serializer_context()
        if request.user.is_authenticated:
            user_follows = SponsorFollow.objects.filter(follower=request.user)
            follow_map = {f.sponsor_id: f for f in user_follows}
        else:
            follow_map = {}
        if page is not None:
            serializer = self.get_serializer(page, many=True, context=serializer_context)
            data = serializer.data
            for item in data:
                sponsor_id = item.get('id')
                follow = follow_map.get(sponsor_id)
                item['is_following'] = follow is not None
                item['follow_id'] = follow.pk if follow else None
                item['notifications_enabled'] = follow.notifications_enabled if follow else None
            return self.get_paginated_response(data)
        serializer = self.get_serializer(qs, many=True, context=serializer_context)
        data = serializer.data
        for item in data:
            sponsor_id = item.get('id')
            follow = follow_map.get(sponsor_id)
            item['is_following'] = follow is not None
            item['follow_id'] = follow.pk if follow else None
            item['notifications_enabled'] = follow.notifications_enabled if follow else None
        return Response(data)

    @action(detail=True, methods=['post'])
    def follow(self, request, pk=None):
        profile = self.get_object()
        follow, created = SponsorFollow.objects.get_or_create(
            follower=request.user,
            sponsor=profile
        )
        if not created:
            follow.delete()
            return Response({'following': False})
        return Response({
            'following': True,
            'follow_id': follow.id,
            'notifications_enabled': follow.notifications_enabled,
        })

class EventSponsorViewSet(ModelViewSet):
    serializer_class = EventSponsorSerializer
    queryset = EventSponsor.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        event_id = self.request.query_params.get('event')
        if event_id:
            qs = qs.filter(event_id=event_id)
        return qs

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

    def get_queryset(self):
        qs = super().get_queryset()
        event_id = self.request.query_params.get('event')
        if event_id:
            qs = qs.filter(event_id=event_id)
        return qs.order_by('-application_date')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def by_event(self, request):
        """Get all sponsorship applications for an event."""
        event_id = request.query_params.get('event_id')
        if not event_id:
            return Response({'error': 'event_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        applications = EventSponsorshipApplication.objects.filter(event_id=event_id).order_by('-application_date')
        serializer = self.get_serializer(applications, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_applications(self, request):
        """Get the current user's sponsorship applications."""
        applications = EventSponsorshipApplication.objects.filter(user=request.user).order_by('-application_date')
        serializer = self.get_serializer(applications, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a sponsorship application. Only event organizer or staff can approve."""
        application = self.get_object()
        event = application.event

        if event.created_by != request.user and not request.user.is_staff:
            return Response({'error': 'Only the event organizer can approve sponsorship applications'}, status=status.HTTP_403_FORBIDDEN)

        approval_reason = request.data.get('reason', 'Application meets sponsorship criteria.')
        
        # Prevent duplicate approvals
        if EventSponsorshipApproval.objects.filter(application=application, approval_status='approved').exists():
            return Response({'error': 'This application has already been approved'}, status=status.HTTP_400_BAD_REQUEST)

        EventSponsorshipApproval.objects.create(
            application=application,
            approval_status='approved',
            approval_reason=approval_reason
        )

        # Auto-create a sponsor entry if level is specified
        level_id = request.data.get('sponsorship_level_id')
        if level_id:
            try:
                level = EventSponsorshipLevel.objects.get(id=level_id, event=event)
                EventSponsor.objects.get_or_create(
                    event=event,
                    sponsor_name=application.applicant_name,
                    defaults={
                        'sponsorship_level': level.level_name,
                        'contribution_amount': level.level_price,
                    }
                )
            except EventSponsorshipLevel.DoesNotExist:
                pass

        return Response({
            'message': f'Sponsorship application from {application.applicant_name} approved.',
            'application_id': str(application.id),
        })

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a sponsorship application."""
        application = self.get_object()
        event = application.event

        if event.created_by != request.user and not request.user.is_staff:
            return Response({'error': 'Only the event organizer can reject sponsorship applications'}, status=status.HTTP_403_FORBIDDEN)

        rejection_reason = request.data.get('reason', 'Application did not meet sponsorship requirements.')

        EventSponsorshipRejection.objects.create(
            application=application,
            rejection_status='rejected',
            rejection_reason=rejection_reason
        )

        return Response({
            'message': f'Sponsorship application from {application.applicant_name} rejected.',
            'application_id': str(application.id),
        })

    @action(detail=False, methods=['get'])
    def sponsorship_dashboard(self, request):
        """Aggregate sponsorship stats for an event."""
        event_id = request.query_params.get('event_id')
        if not event_id:
            return Response({'error': 'event_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)

        applications = EventSponsorshipApplication.objects.filter(event=event)
        approved_ids = EventSponsorshipApproval.objects.filter(
            application__event=event, approval_status='approved'
        ).values_list('application_id', flat=True)
        rejected_ids = EventSponsorshipRejection.objects.filter(
            application__event=event, rejection_status='rejected'
        ).values_list('application_id', flat=True)

        levels = EventSponsorshipLevel.objects.filter(event=event)
        sponsors = EventSponsor.objects.filter(event=event)

        total_sponsorship = sum(float(s.contribution_amount or 0) for s in sponsors)

        return Response({
            'event_id': str(event.id),
            'event_name': event.name,
            'total_applications': applications.count(),
            'approved': applications.filter(id__in=approved_ids).count(),
            'rejected': applications.filter(id__in=rejected_ids).count(),
            'pending': applications.exclude(id__in=approved_ids).exclude(id__in=rejected_ids).count(),
            'total_sponsors': sponsors.count(),
            'total_sponsorship_value': total_sponsorship,
            'levels': [{
                'id': str(l.id),
                'name': l.level_name,
                'benefits': l.level_benefits,
                'price': float(l.level_price),
            } for l in levels],
            'sponsors': [{
                'name': s.sponsor_name,
                'level': s.sponsorship_level if hasattr(s, 'sponsorship_level') else '',
                'amount': float(s.contribution_amount or 0),
            } for s in sponsors],
        })

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

    def get_queryset(self):
        qs = super().get_queryset()
        event_id = self.request.query_params.get('event')
        if event_id:
            qs = qs.filter(event_id=event_id)
        return qs

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

    def get_queryset(self):
        qs = EventSurvey.objects.all()
        event_id = self.request.query_params.get('event')
        if event_id:
            qs = qs.filter(event_id=event_id)
        return qs

class EventSurveyQuestionViewSet(ModelViewSet):
    serializer_class = EventSurveyQuestionSerializer
    queryset = EventSurveyQuestion.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = EventSurveyQuestion.objects.all()
        survey_id = self.request.query_params.get('survey')
        if survey_id:
            qs = qs.filter(survey_id=survey_id)
        return qs

class EventSurveyResponseViewSet(ModelViewSet):
    serializer_class = EventSurveyResponseSerializer
    queryset = EventSurveyResponse.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = EventSurveyResponse.objects.all()
        question_id = self.request.query_params.get('question')
        if question_id:
            qs = qs.filter(question_id=question_id)
        user_id = self.request.query_params.get('user')
        if user_id:
            qs = qs.filter(user_id=user_id)
        return qs

class EventSurveyTemplateViewSet(ModelViewSet):
    serializer_class = EventSurveyTemplateSerializer
    queryset = EventSurveyTemplate.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = EventSurveyTemplate.objects.all()
        if not self.request.user.is_authenticated:
            return qs.filter(is_platform=True)
        return qs.filter(
            Q(is_platform=True) | Q(created_by=self.request.user)
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

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
    lookup_field = 'uuid'
    filterset_fields = ['event', 'user', 'booking_status']

    @action(detail=False, methods=['post'])
    def book_slot(self, request):
        """Book a slot for an event. Accepts attendees array with per-person info."""
        event_uuid = request.data.get('event_uuid')
        event_id = request.data.get('event_id')
        ticket_tier_id = request.data.get('ticket_tier_id')
        ticket_id = request.data.get('ticket_id')
        attendees = request.data.get('attendees', [])
        group_name = request.data.get('group_name', '')
        quantity = int(request.data.get('quantity', 1))

        try:
            if event_uuid:
                event = Event.objects.get(uuid=event_uuid)
            else:
                event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)

        user_profile = getattr(request.user, 'profile', None)
        user_age = None
        if user_profile and user_profile.birth_date:
            today = datetime.today()
            dob = user_profile.birth_date
            user_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        tier = None
        ticket = None

        if ticket_tier_id:
            try:
                tier = TicketTier.objects.get(pk=ticket_tier_id, event=event)
                if not tier.is_active:
                    return Response({'error': 'This ticket tier is no longer available.'}, status=status.HTTP_400_BAD_REQUEST)
            except TicketTier.DoesNotExist:
                return Response({'error': 'Ticket tier not found'}, status=status.HTTP_404_NOT_FOUND)
        elif ticket_id:
            try:
                ticket = EventTicket.objects.get(pk=ticket_id, event=event)
            except EventTicket.DoesNotExist:
                return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            ticket = event.tickets.first()
            if not ticket:
                ticket = EventTicket.objects.create(
                    event=event, ticket_type='regular', price=0.00,
                    quantity_available=event.capacity, is_free=True
                )

        is_free = True
        unit_price = 0.00
        if tier:
            if tier.price and float(tier.price) > 0:
                is_free = False
                unit_price = float(tier.price)
            if tier.min_age and (user_age is None or user_age < tier.min_age):
                return Response({'error': f'You must be at least {tier.min_age} to buy {tier.name}.'}, status=status.HTTP_403_FORBIDDEN)
            if tier.max_age and (user_age is None or user_age > tier.max_age):
                return Response({'error': f'You must be under {tier.max_age} to buy {tier.name}.'}, status=status.HTTP_403_FORBIDDEN)
            tier_booked = EventSlotBooking.objects.filter(ticket_tier=tier, booking_status__in=['confirmed', 'checked_in']).aggregate(
                total=models.Sum('quantity')
            )['total'] or 0
            requested_people = max(len(attendees), quantity * tier.group_size)
            if tier_booked + requested_people > tier.capacity:
                return Response({'error': f'Tier "{tier.name}" capacity exceeded.'}, status=status.HTTP_400_BAD_REQUEST)
        elif ticket:
            if not ticket.is_free and float(ticket.price) > 0:
                is_free = False
                unit_price = float(ticket.price)

        total_people = max(len(attendees), quantity * (tier.group_size if tier else 1))

        confirmed = event.slot_bookings.filter(booking_status__in=['confirmed', 'checked_in']).aggregate(
            total=models.Sum('quantity')
        )['total'] or 0
        if confirmed + total_people > event.capacity:
            return Response({'error': f'Event capacity exceeded. Only {event.capacity - confirmed} slots left.'}, status=status.HTTP_400_BAD_REQUEST)

        # Per-person limit: total people across all user's bookings
        MAX_FREE_PEOPLE = 1
        MAX_PAID_PEOPLE = 5
        max_allowed = MAX_FREE_PEOPLE if is_free else MAX_PAID_PEOPLE
        existing_people = EventSlotBooking.objects.filter(
            event=event, user=request.user,
            booking_status__in=['confirmed', 'checked_in', 'pending']
        ).aggregate(total=models.Sum('quantity'))['total'] or 0
        if existing_people + total_people > max_allowed:
            remaining = max(0, max_allowed - existing_people)
            return Response({
                'error': f'Maximum {max_allowed} {"person" if max_allowed == 1 else "people"} per event. You can book for {remaining} more.'
            }, status=status.HTTP_400_BAD_REQUEST)

        bookings_created = []
        category = tier.category if tier else 'individual'
        amount = unit_price * total_people

        if category in ('couple', 'group'):
            holder = attendees[0] if attendees else {}
            booking = EventSlotBooking.objects.create(
                event=event,
                user=request.user,
                ticket=ticket,
                ticket_tier=tier,
                quantity=total_people,
                booking_status='confirmed' if is_free else 'pending',
                amount_paid=amount,
                attendee_name=holder.get('name', ''),
                attendee_email=holder.get('email', ''),
                attendee_phone=holder.get('phone', ''),
                attendee_age=user_age,
                group_name=group_name,
                attendees=attendees,
            )
            bookings_created.append(booking)
        else:
            for attendee in attendees:
                booking = EventSlotBooking.objects.create(
                    event=event,
                    user=request.user,
                    ticket=ticket,
                    ticket_tier=tier,
                    quantity=1,
                    booking_status='confirmed' if is_free else 'pending',
                    amount_paid=unit_price,
                    attendee_name=attendee.get('name', ''),
                    attendee_email=attendee.get('email', ''),
                    attendee_phone=attendee.get('phone', ''),
                    attendee_age=user_age,
                )
                bookings_created.append(booking)

        EventInteractionAnalytics.objects.create(
            event=event, user=request.user, interaction_type='ticket_click',
            viewer_age=user_age
        )

        serializer = EventSlotBookingSerializer(bookings_created, many=True)
        return Response({
            'message': 'Tickets booked successfully!' if is_free else 'Booking created. Please complete payment.',
            'purchases': serializer.data,
            'is_free': is_free,
            'quantity': total_people,
            'requires_payment': not is_free,
            'category': category,
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def my_bookings(self, request):
        """Get all bookings for the current user, including tickets shared with them"""
        owned = EventSlotBooking.objects.filter(user=request.user)
        shared_ids = []
        for booking in EventSlotBooking.objects.exclude(user=request.user).exclude(shared_with=[]):
            if str(request.user.id) in (booking.shared_with or []):
                shared_ids.append(booking.id)
        shared = EventSlotBooking.objects.filter(id__in=shared_ids) if shared_ids else EventSlotBooking.objects.none()
        bookings = (owned | shared).distinct().order_by('-booked_at')
        serializer = EventSlotBookingSerializer(bookings, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def share_ticket(self, request, pk=None):
        """Share a ticket with another user by ID or email"""
        booking = self.get_object()
        if booking.user != request.user:
            return Response({'error': 'You can only share your own tickets'}, status=status.HTTP_403_FORBIDDEN)

        target_user_id = request.data.get('user_id')
        target_email = request.data.get('email')

        if not target_user_id and not target_email:
            return Response({'error': 'Provide user_id or email of the user to share with'}, status=status.HTTP_400_BAD_REQUEST)

        if target_user_id:
            try:
                target = CustomUser.objects.get(pk=target_user_id)
            except CustomUser.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            try:
                target = CustomUser.objects.get(email=target_email)
            except CustomUser.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        shared = booking.shared_with or []
        target_id_str = str(target.id)
        if target_id_str not in shared:
            shared.append(target_id_str)
            booking.shared_with = shared
            booking.save()

        return Response({'message': f'Ticket shared with {target.email}'})

    @action(detail=True, methods=['post'])
    def unshare_ticket(self, request, pk=None):
        """Remove a user from shared access"""
        booking = self.get_object()
        if booking.user != request.user:
            return Response({'error': 'You can only manage your own tickets'}, status=status.HTTP_403_FORBIDDEN)

        target_user_id = request.data.get('user_id')
        if not target_user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        shared = booking.shared_with or []
        target_id_str = str(target_user_id)
        if target_id_str in shared:
            shared.remove(target_id_str)
            booking.shared_with = shared
            booking.save()

        return Response({'message': 'User removed from shared ticket'})

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
                'category': tier.category,
                'tier': tier.tier,
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


class SponsorApplicationViewSet(ModelViewSet):
    serializer_class = SponsorApplicationSerializer
    queryset = SponsorApplication.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        event_id = self.request.query_params.get('event')
        if event_id:
            qs = qs.filter(events__id=event_id)
        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def my_applications(self, request):
        applications = SponsorApplication.objects.filter(user=request.user).order_by('-created_at')
        serializer = self.get_serializer(applications, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def incoming_requests(self, request):
        applications = SponsorApplication.objects.filter(
            events__created_by=request.user
        ).exclude(
            user=request.user
        ).distinct().order_by('-created_at')
        serializer = self.get_serializer(applications, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        application = self.get_object()
        if request.user != application.user and not request.user.is_staff:
            has_event_access = application.events.filter(created_by=request.user).exists()
            if not has_event_access:
                return Response({'error': 'Not authorized to approve this application'}, status=status.HTTP_403_FORBIDDEN)

        application.status = 'approved'
        application.save()

        for event in application.events.all():
            EventSponsor.objects.get_or_create(
                event=event,
                sponsor_name=application.applicant_name,
                defaults={
                    'organisation': application.organisation,
                    'sponsor_rep': application.user,
                    'sponsor_details': application.application_details[:1000],
                }
            )

        return Response({'message': f'Sponsorship application from {application.applicant_name} approved.'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        application = self.get_object()
        if request.user != application.user and not request.user.is_staff:
            has_event_access = application.events.filter(created_by=request.user).exists()
            if not has_event_access:
                return Response({'error': 'Not authorized to reject this application'}, status=status.HTTP_403_FORBIDDEN)

        application.status = 'rejected'
        application.save()
        return Response({'message': f'Sponsorship application from {application.applicant_name} rejected.'})

    @action(detail=False, methods=['post'])
    def bulk_apply(self, request):
        event_ids = request.data.get('event_ids', [])
        if not event_ids:
            return Response({'error': 'event_ids list is required'}, status=status.HTTP_400_BAD_REQUEST)

        events = Event.objects.filter(id__in=event_ids)
        if not events.exists():
            return Response({'error': 'No valid events found'}, status=status.HTTP_400_BAD_REQUEST)

        application = SponsorApplication.objects.create(
            user=request.user,
            applicant_name=request.data.get('applicant_name', request.user.get_full_name() or request.user.email),
            applicant_contact=request.data.get('applicant_contact', request.user.email),
            application_details=request.data.get('application_details', ''),
        )
        if request.data.get('organisation'):
            from Organisation.models import Organisation
            try:
                application.organisation = Organisation.objects.get(pk=request.data['organisation'])
            except Organisation.DoesNotExist:
                pass
        application.events.set(events)
        application.save()

        serializer = self.get_serializer(application)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SponsorshipNegotiationViewSet(ModelViewSet):
    serializer_class = SponsorshipNegotiationSerializer
    queryset = SponsorshipNegotiation.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=['post'])
    def negotiate(self, request, pk=None):
        negotiation = self.get_object()
        terms = request.data.get('terms')
        message = request.data.get('message')

        if terms:
            if negotiation.status == 'proposed':
                negotiation.counter_terms = terms
                negotiation.status = 'countered'
            else:
                negotiation.terms = terms
                negotiation.status = 'proposed'

        if message:
            msgs = negotiation.messages or []
            msgs.append({
                'sender': request.user.email,
                'message': message,
                'timestamp': timezone.now().isoformat()
            })
            negotiation.messages = msgs

        negotiation.save()
        serializer = self.get_serializer(negotiation)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        negotiation = self.get_object()
        negotiation.status = 'accepted'
        negotiation.save()

        application = negotiation.application
        application.status = 'approved'
        application.save()

        return Response({'message': 'Negotiation accepted.', 'status': 'accepted'})

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        negotiation = self.get_object()
        negotiation.status = 'declined'
        negotiation.save()
        return Response({'message': 'Negotiation declined.', 'status': 'declined'})

    @action(detail=True, methods=['post'])
    def counter(self, request, pk=None):
        negotiation = self.get_object()
        counter_terms = request.data.get('counter_terms')
        message = request.data.get('message')

        if counter_terms:
            negotiation.counter_terms = counter_terms
        negotiation.status = 'countered'

        if message:
            msgs = negotiation.messages or []
            msgs.append({
                'sender': request.user.email,
                'message': message,
                'timestamp': timezone.now().isoformat()
            })
            negotiation.messages = msgs

        negotiation.save()
        serializer = self.get_serializer(negotiation)
        return Response(serializer.data)


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
        if user_profile and user_profile.birth_date:
            today = datetime.today()
            dob = user_profile.birth_date
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


class OrganizerFollowViewSet(ModelViewSet):
    serializer_class = OrganizerFollowSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return OrganizerFollow.objects.filter(follower=self.request.user)

    def perform_create(self, serializer):
        serializer.save(follower=self.request.user)

    @action(detail=False, methods=['get'])
    def following(self, request):
        qs = OrganizerFollow.objects.filter(follower=request.user)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def followers(self, request):
        qs = OrganizerFollow.objects.filter(organizer__user=request.user)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def toggle_notifications(self, request, pk=None):
        follow = self.get_object()
        enabled = request.data.get('notifications_enabled')
        if enabled is None:
            follow.notifications_enabled = not follow.notifications_enabled
        else:
            follow.notifications_enabled = bool(enabled)
        follow.save(update_fields=['notifications_enabled'])
        serializer = self.get_serializer(follow)
        return Response(serializer.data)


class SponsorFollowViewSet(ModelViewSet):
    serializer_class = SponsorFollowSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return SponsorFollow.objects.filter(follower=self.request.user)

    def perform_create(self, serializer):
        serializer.save(follower=self.request.user)

    @action(detail=False, methods=['get'])
    def following(self, request):
        qs = SponsorFollow.objects.filter(follower=request.user)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def followers(self, request):
        qs = SponsorFollow.objects.filter(sponsor__user=request.user)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def toggle_notifications(self, request, pk=None):
        follow = self.get_object()
        enabled = request.data.get('notifications_enabled')
        if enabled is None:
            follow.notifications_enabled = not follow.notifications_enabled
        else:
            follow.notifications_enabled = bool(enabled)
        follow.save(update_fields=['notifications_enabled'])
        serializer = self.get_serializer(follow)
        return Response(serializer.data)


class PartnershipInvitationViewSet(ModelViewSet):
    serializer_class = PartnershipInvitationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PartnershipInvitation.objects.filter(
            models.Q(sender=self.request.user) | models.Q(receiver__user=self.request.user)
        )

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    @action(detail=False, methods=['get'])
    def inbox(self, request):
        qs = PartnershipInvitation.objects.filter(receiver__user=request.user, status='pending')
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        inv = self.get_object()
        inv.status = 'accepted'
        inv.save()
        return Response({'status': 'accepted'})

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        inv = self.get_object()
        inv.status = 'declined'
        inv.save()
        return Response({'status': 'declined'})


class CoOrganizerViewSet(ModelViewSet):
    serializer_class = CoOrganizerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CoOrganizer.objects.filter(
            models.Q(user=self.request.user) | models.Q(event__created_by=self.request.user)
        )

    def perform_create(self, serializer):
        serializer.save(added_by=self.request.user)
