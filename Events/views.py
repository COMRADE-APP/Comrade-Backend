from django.shortcuts import render
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ModelViewSet
from Events.serializers import EventSerializer
from Events.models import Event, EventCategory, EventAttendance, EventBudget, EventCategoryAssignment, EventCollaboration, EventFeedback, EventFeedbackResponse, EventFile, EventFollowUp, EventLogistics, EventMediaCoverage, EventPartnership, EventPhoto, EventPromotion, EventRegistration, EventReminder, EventSchedule, EventSession, EventSpeaker, EventSponsor, EventSponsorAgreement, EventSponsorBenefit, EventSponsorLogo, EventSponsorPackage, EventSponsorPayment, EventSponsorshipAgreementDocument, EventSponsorshipApplication, EventSponsorshipApproval, EventSponsorshipCertificate, EventSponsorshipContract, EventSponsorshipDowngrade, EventSponsorshipEvaluation, EventSponsorshipExtension, EventSponsorshipFeedback, EventSponsorshipHistory, EventSponsorshipInvoice, EventSponsorshipLetter, EventSponsorshipLevel, EventSponsorshipRecognition, EventSponsorshipRejection, EventSponsorshipRenewal, EventSponsorshipReport, EventSponsorshipTermination, EventSponsorshipTransfer, EventSponsorshipUpgrade, EventSurvey, EventSurveyQuestion, EventSurveyResponse, EventTag, EventTagAssignment, EventTicket, EventVideo, EventReport, EventInvitation, EventLike, EventVisibility, VisibilityLog
from Events.serializers import EventSerializer, EventCategorySerializer, EventAttendanceSerializer, EventBudgetSerializer, EventCategoryAssignmentSerializer, EventCollaborationSerializer, EventFeedbackSerializer, EventFeedbackResponseSerializer, EventFileSerializer, EventFollowUpSerializer, EventLogisticsSerializer, EventMediaCoverageSerializer, EventPartnershipSerializer, EventPhotoSerializer, EventPromotionSerializer, EventRegistrationSerializer, EventReminderSerializer, EventScheduleSerializer, EventSessionSerializer, EventSpeakerSerializer, EventSponsorSerializer, EventSponsorAgreementSerializer, EventSponsorBenefitSerializer, EventSponsorLogoSerializer, EventSponsorPackageSerializer, EventSponsorPaymentSerializer, EventSponsorshipAgreementDocumentSerializer, EventSponsorshipApplicationSerializer, EventSponsorshipApprovalSerializer, EventSponsorshipCertificateSerializer, EventSponsorshipContractSerializer, EventSponsorshipDowngradeSerializer, EventSponsorshipEvaluationSerializer, EventSponsorshipExtensionSerializer, EventSponsorshipFeedbackSerializer, EventSponsorshipHistorySerializer, EventSponsorshipInvoiceSerializer, EventSponsorshipLetterSerializer, EventSponsorshipLevelSerializer, EventSponsorshipRecognitionSerializer, EventSponsorshipRejectionSerializer, EventSponsorshipRenewalSerializer, EventSponsorshipReportSerializer, EventSponsorshipTerminationSerializer, EventSponsorshipTransferSerializer, EventSponsorshipUpgradeSerializer, EventSurveySerializer, EventSurveyQuestionSerializer, EventSurveyResponseSerializer, EventTagSerializer, EventTagAssignmentSerializer, EventTicketSerializer, EventVideoSerializer, EventReportSerializer, EventInvitationSerializer, EventLikeSerializer, EventVisibilitySerializer, VisibilityLogSerializer
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
# Create your views here.


class EventViewSet(ModelViewSet):
    serializer_class = EventSerializer
    queryset = Event.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination
    filter_backends = [SearchFilter, OrderingFilter]
    lookup_field = 'id'
    search_fields = ['id', 'name', 'description', 'location']
    filterset_fields = ['event_date', 'location', 'created_by', 'status', 'complexity_level']

    def perform_create(self, serializer):
        """Auto-set created_by to the authenticated user and optionally link to a room"""
        instance = serializer.save(created_by=self.request.user)
        
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
    #     event = Event.objects.create(
    #         name=request.data['name'],
    #         description=request.data['description'],
    #         location=request.data['location'],
    #         date=request.data['date'],
    #         end_date=request.data['end_date'],
    #         start_time=request.data['start_time'],
    #         end_time=request.data['end_time'],
    #         url=request.data['url'],
    #         visibility=request.data['visibility'],
    #         event_type=request.data['event_type'],
    #         max_attendees=request.data['max_attendees'],
    #         is_ticketed=request.data['is_ticketed'],
    #         ticket_price=request.data['ticket_price'],
    #         status=request.data['status'],
    #         created_by=request.user,
    #         event_url=request.data['event_url'],
    #         event_location=request.data['event_location'],
    #         event_type=request.data['event_type'],
    #         booking_deadline=request.data['event_booking_deadline'],
    #         max_attendees=request.data['event_max_attendees'],
    #         is_ticketed=request.data['event_is_ticketed'],
    #         ticket_price=request.data['event_ticket_price'],
    #         status=request.data['event_status'],
    #         created_by=request.user,
    #         end_time=request.data['end_time'],
    #         end_date=request.data['end_date'],
    #     )
    #     serializer = self.get_serializer(event)
    #     return Response(serializer.data, status=status.HTTP_200_OK)

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

