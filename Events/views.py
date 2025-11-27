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
from Authentication.models import Profile
from Rooms.models import Room, DefaultRoom, DirectMessage
from urllib.parse import quote
from django.core.mail import send_mail
# Create your views here.


class EventViewSet(ModelViewSet):
    serializer_class = EventSerializer
    queryset = Event.objects.all()
    permission_classes = [IsModerator]
    pagination_class = PageNumberPagination
    filter_backends = [SearchFilter, OrderingFilter]
    lookup_field = 'title'
    search_fields = ['title', 'description', 'location']
    filterset_fields = ['date', 'location', 'created_by']

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
        events = Event.objects.filter(date__gte=now).order_by('date')
        page = self.paginate_queryset(events)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def past_events(self, request):
        now = timezone.now()
        events = Event.objects.filter(date__lt=now).order_by('-date')
        page = self.paginate_queryset(events)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def rsvp(self, request, id=None):
        event = self.get_object()
        user = request.user
        event.attendees.add(user)
        event.save()
        return Response({'status': 'RSVP successful'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def cancel_rsvp(self, request, id=None):
        event = self.get_object()
        user = request.user
        event.attendees.remove(user)
        event.save()
        return Response({'status': 'RSVP cancelled'}, status=status.HTTP_200_OK)
    
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def rate(self, request, id=None):
        event = self.get_object()
        rating_value = request.data.get('rating')
        if rating_value and 1 <= int(rating_value) <= 5:
            from Events.models import EventFeedback
            rating, created = EventFeedback.objects.get_or_create(event=event, user=request.user)
            rating.rating = rating_value
            rating.save()
            return Response({'status': 'Event rated'}, status=status.HTTP_200_OK)
        return Response({'error': 'Rating value must be between 1 and 5'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def rating(self, request, id=None):
        event = self.get_object()
        from Events.models import EventFeedback
        ratings = EventFeedback.objects.filter(event=event)
        if ratings.exists():
            average_rating = ratings.aggregate(models.Avg('rating'))['rating__avg']
            return Response({'average_rating': average_rating}, status=status.HTTP_200_OK)
        return Response({'average_rating': 0}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def bookmark(self, request, id=None):
        event = self.get_object()
        user = request.user
        bookmarked_events = Pin.objects.create(user=user, event=event)
        bookmarked_events.save()
        return Response({'status': 'Event bookmarked'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def remove_bookmark(self, request, id=None):
        event = self.get_object()
        user = request.user
        Pin.objects.filter(user=user, event=event).delete()
        return Response({'status': 'Bookmark removed'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def is_bookmarked(self, request, id=None):  
        event = self.get_object()
        user = request.user
        is_bookmarked = Pin.objects.filter(user=user, event=event).exists()
        return Response({'is_bookmarked': is_bookmarked}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def attendees(self, request, id=None):
        event = self.get_object()
        attendees = event.attendees.all()
        attendees_data = [{'id': attendee.id, 'username': attendee.username} for attendee in attendees]
        return Response(attendees_data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def attendee_count(self, request, id=None):
        event = self.get_object()
        count = event.attendees.count()
        return Response({'attendee_count': count}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def share(self, request, id=None):
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
    def schedule_event(self, request, pk=None):
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
    
    
    
    '''Block according to the creator'''

class EventVisibilityViewSet(ModelViewSet):
    serializer_class = EventVisibilitySerializer
    queryset = EventVisibility.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=['post'])
    def create_visibility(self, request):
        '''Set material availability period'''
        pass
    
    '''Add to blocked list'''
    '''Restrict rooms'''

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

class EventFeedbackResponseViewSet(ModelViewSet):
    serializer_class = EventFeedbackResponseSerializer
    queryset = EventFeedbackResponse.objects.all()
    permission_classes = [IsModerator]

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def respond(self, request, id=None):
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
    def block_from_creator(self, request, id=None):
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
    def unblock_from_creator(self, request, id=None):
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
    def share_event(self, request, id=None):
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
    def comment(self, request, id=None):
        event = self.get_object()
        user = request.user
        comment_text = request.data.get('comment')
        if comment_text:
            comment = EventLike.objects.create(event=event, user=user, comment=comment_text)
            comment.save()
            return Response({'status': 'Comment added'}, status=status.HTTP_200_OK)
        return Response({'error': 'Comment text is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def comments(self, request, id=None):
        event = self.get_object()
        comments = EventLike.objects.filter(event=event).order_by('-created_on')
        serializer = EventLikeSerializer(comments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def like(self, request, id=None):
        event = self.get_object()
        user = request.user

        if not event:
            return Response({'error': 'No event was parsed from the frontend.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        event = EventLike.objects.filter(event=event, user=user)
        if not event:
            event = EventLike.objects.create(event=event, user=user)
        
        event.like = True
        event.save()
        return Response({'status': 'Event liked'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unlike(self, request, id=None):
        event = self.get_object()
        user = request.user

        if not event:
            return Response({'error': 'No event was parsed from the frontend.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        event = EventLike.objects.filter(event=event, user=user)
        if not event:
            event = EventLike.objects.create(event=event, user=user)
        
        event.unlike = True
        event.save()
        return Response({'status': 'Event unliked'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def likes(self, request, id=None):
        event = self.get_object()
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
    def book_slot(self, request, id=None):
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

