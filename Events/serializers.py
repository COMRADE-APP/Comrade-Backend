from Events.models import Event, EventCategory, EventAttendance, EventBudget, EventCategoryAssignment, EventCollaboration, EventFeedback, EventFeedbackResponse, EventFile, EventFollowUp, EventLogistics, EventMediaCoverage, EventPartnership, EventPhoto, EventPromotion, EventRegistration, EventReminder, EventSchedule, EventSession, EventSpeaker, EventSponsor, EventSponsorAgreement, EventSponsorBenefit, EventSponsorLogo, EventSponsorPackage, EventSponsorPayment, EventSponsorshipAgreementDocument, EventSponsorshipApplication, EventSponsorshipApproval, EventSponsorshipCertificate, EventSponsorshipContract, EventSponsorshipDowngrade, EventSponsorshipEvaluation, EventSponsorshipExtension, EventSponsorshipFeedback, EventSponsorshipHistory, EventSponsorshipInvoice, EventSponsorshipLetter, EventSponsorshipLevel, EventSponsorshipRecognition, EventSponsorshipRejection, EventSponsorshipRenewal, EventSponsorshipReport, EventSponsorshipTermination, EventSponsorshipTransfer, EventSponsorshipUpgrade, EventSurvey, EventSurveyQuestion, EventSurveyResponse, EventTag, EventTagAssignment, EventTicket, EventVideo, EventReport, EventInvitation, EventLike, EventVisibility, VisibilityLog, EventSlotBooking, TicketTier, EventMaterial, EventInteractionAnalytics, SponsorRequest, OrganizerProfile, SponsorProfile, OrganizerFollow, SponsorFollow, PartnershipInvitation, CoOrganizer, SponsorApplication, SponsorshipNegotiation
from rest_framework.serializers import ModelSerializer, Serializer
from rest_framework import serializers
from datetime import datetime
from Announcements.models import Pin
from django.db.models import Sum

class TicketTierSerializer(ModelSerializer):
    class Meta:
        model = TicketTier
        fields = '__all__'

class EventMaterialSerializer(ModelSerializer):
    class Meta:
        model = EventMaterial
        fields = '__all__'

class EventInteractionAnalyticsSerializer(ModelSerializer):
    class Meta:
        model = EventInteractionAnalytics
        fields = '__all__'

class EventSerializer(ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    created_by_avatar = serializers.SerializerMethodField()
    event_organizer_name = serializers.SerializerMethodField()
    slots_remaining = serializers.SerializerMethodField()
    tickets_available = serializers.SerializerMethodField()
    ticket_tiers = TicketTierSerializer(many=True, read_only=True)
    materials = EventMaterialSerializer(many=True, read_only=True)
    user_reaction = serializers.SerializerMethodField()
    is_pinned = serializers.SerializerMethodField()
    is_interested = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    event_organizer_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = '__all__'
        read_only_fields = ['time_stamp', 'created_by']

    def get_slots_remaining(self, obj):
        confirmed = obj.slot_bookings.filter(booking_status__in=['confirmed', 'checked_in']).aggregate(
            total=Sum('quantity')
        )['total'] or 0
        return max(0, obj.capacity - confirmed)



    def get_tickets_available(self, obj):
        tickets = obj.tickets.all()
        if tickets.exists():
            return [{
                'id': t.id,
                'ticket_type': t.ticket_type,
                'price': str(t.price),
                'is_free': t.is_free,
                'quantity_available': t.quantity_available,
            } for t in tickets]
        return []

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.email
        return None

    def get_event_organizer_name(self, obj):
        if obj.event_organizer:
            name = f"{obj.event_organizer.user.first_name} {obj.event_organizer.user.last_name}".strip()
            if name:
                return f"{name} ({obj.event_organizer.business_name})"
            return obj.event_organizer.business_name
        return None

    def get_created_by_avatar(self, obj):
        if obj.created_by:
            try:
                profile = obj.created_by.profile
                if profile and profile.profile_picture:
                    request = self.context.get('request')
                    if request:
                        return request.build_absolute_uri(profile.profile_picture.url)
                    return profile.profile_picture.url
            except Exception:
                pass
            try:
                user_profile = obj.created_by.user_profile
                if user_profile and user_profile.avatar:
                    request = self.context.get('request')
                    if request:
                        return request.build_absolute_uri(user_profile.avatar.url)
                    return user_profile.avatar.url
            except Exception:
                pass
        return None

    def get_user_reaction(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            like = EventLike.objects.filter(event=obj, user=request.user).first()
            if like:
                return like.reaction
        return None

    def get_is_pinned(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return Pin.objects.filter(user=request.user, events=obj).exists()
        return False

    def get_is_interested(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return EventFeedback.objects.filter(
                event=obj, user=request.user, attendendance_status='interested'
            ).exists()
        return False

    def get_category_name(self, obj):
        assignment = EventCategoryAssignment.objects.filter(event=obj).select_related('category').first()
        return assignment.category.name if assignment else None

    def get_event_organizer_detail(self, obj):
        if not obj.event_organizer:
            return None
        try:
            org = OrganizerProfile.objects.get(pk=obj.event_organizer_id)
            request = self.context.get('request')
            avatar_url = None
            if org.avatar:
                avatar_url = request.build_absolute_uri(org.avatar.url) if request else org.avatar.url
            cover_url = None
            if org.cover_photo:
                cover_url = request.build_absolute_uri(org.cover_photo.url) if request else org.cover_photo.url
            return {
                'id': org.pk,
                'business_name': org.business_name,
                'avatar': avatar_url,
                'cover_photo': cover_url,
                'location': org.location,
            }
        except OrganizerProfile.DoesNotExist:
            return None

    def validate_event_date(self, value):
        from django.utils import timezone
        if value and value < timezone.now():
            raise serializers.ValidationError("Event date cannot be in the past.")
        return value

    def validate_scheduled_time(self, value):
        from django.utils import timezone
        if value and value < timezone.now():
            raise serializers.ValidationError("Scheduled time cannot be in the past.")
        return value
        
class EventVisibilitySerializer(ModelSerializer):
    class Meta:
        model = EventVisibility
        fields = '__all__'

class VisibilityLogSerializer(ModelSerializer):
    class Meta:
        model = VisibilityLog
        fields = '__all__'
        read_only_fields = ['changed_on']

class EventCategorySerializer(ModelSerializer):
    class Meta:
        model = EventCategory
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventAttendanceSerializer(ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()

    class Meta:
        model = EventAttendance
        fields = '__all__'
        read_only_fields = ['check_in_time']

    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email

    def get_user_email(self, obj):
        return obj.user.email

class EventBudgetSerializer(ModelSerializer):
    class Meta:
        model = EventBudget
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventCategoryAssignmentSerializer(ModelSerializer):
    class Meta:
        model = EventCategoryAssignment
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventCollaborationSerializer(ModelSerializer):
    class Meta:
        model = EventCollaboration
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventLikeSerializer(ModelSerializer):
    class Meta:
        model = EventLike
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventFeedbackSerializer(ModelSerializer):
    user_name = serializers.SerializerMethodField()
    response = serializers.SerializerMethodField()

    class Meta:
        model = EventFeedback
        fields = '__all__'
        read_only_fields = ['timestamp']

    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email

    def get_response(self, obj):
        resp = obj.eventfeedbackresponse_set.first()
        if resp:
            return EventFeedbackResponseSerializer(resp).data
        return None

class EventFeedbackResponseSerializer(ModelSerializer):
    class Meta:
        model = EventFeedbackResponse
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventFileSerializer(ModelSerializer):
    class Meta:
        model = EventFile
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventFollowUpSerializer(ModelSerializer):
    class Meta:
        model = EventFollowUp
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventLogisticsSerializer(ModelSerializer):
    class Meta:
        model = EventLogistics
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventMediaCoverageSerializer(ModelSerializer):
    class Meta:
        model = EventMediaCoverage
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventPartnershipSerializer(ModelSerializer):
    class Meta:
        model = EventPartnership
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventPromotionSerializer(ModelSerializer):
    class Meta:
        model = EventPromotion
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventPhotoSerializer(ModelSerializer):
    class Meta:
        model = EventPhoto
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventRegistrationSerializer(ModelSerializer):
    class Meta:
        model = EventRegistration
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventReminderSerializer(ModelSerializer):
    class Meta:
        model = EventReminder
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventScheduleSerializer(ModelSerializer):
    class Meta:
        model = EventSchedule
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorSerializer(ModelSerializer):
    class Meta:
        model = EventSponsor
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSessionSerializer(ModelSerializer):
    class Meta:
        model = EventSession
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorAgreementSerializer(ModelSerializer):
    class Meta:
        model = EventSponsorAgreement
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorshipApplicationSerializer(ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = EventSponsorshipApplication
        fields = '__all__'
        read_only_fields = ['user', 'application_date']

    def get_status(self, obj):
        if EventSponsorshipApproval.objects.filter(application=obj, approval_status='approved').exists():
            return 'approved'
        if EventSponsorshipRejection.objects.filter(application=obj, rejection_status='rejected').exists():
            return 'rejected'
        return 'pending'

class EventSpeakerSerializer(ModelSerializer):
    class Meta:
        model = EventSpeaker
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorBenefitSerializer(ModelSerializer):
    class Meta:
        model = EventSponsorBenefit
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorPaymentSerializer(ModelSerializer):
    class Meta:
        model = EventSponsorPayment
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorLogoSerializer(ModelSerializer):
    class Meta:
        model = EventSponsorLogo
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorPackageSerializer(ModelSerializer):
    class Meta:
        model = EventSponsorPackage
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorshipAgreementDocumentSerializer(ModelSerializer):
    class Meta:
        model = EventSponsorshipAgreementDocument
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorshipRejectionSerializer(ModelSerializer):
    class Meta:
        model = EventSponsorshipRejection
        fields = '__all__'
        read_only_fields = ['timestamp']

class SponsorRequestSerializer(ModelSerializer):
    organization_name = serializers.SerializerMethodField()

    class Meta:
        model = SponsorRequest
        fields = '__all__'
        read_only_fields = ['sent_date', 'created_by']

    def get_organization_name(self, obj):
        return obj.organization.name if obj.organization else None

class OrganizerProfileSerializer(ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    follower_count = serializers.SerializerMethodField()

    class Meta:
        model = OrganizerProfile
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at']
        extra_kwargs = {
            'cover_photo': {'required': False, 'allow_null': True},
        }

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.email

    def get_follower_count(self, obj):
        return getattr(obj, 'follower_count', None) or obj.followers.count()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request:
            if data.get('avatar'):
                data['avatar'] = request.build_absolute_uri(instance.avatar.url)
            if data.get('cover_photo'):
                data['cover_photo'] = request.build_absolute_uri(instance.cover_photo.url)
        return data

class SponsorProfileSerializer(ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    follower_count = serializers.SerializerMethodField()

    class Meta:
        model = SponsorProfile
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at']

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.email

    def get_follower_count(self, obj):
        return getattr(obj, 'follower_count', None) or obj.followers.count()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request:
            if data.get('logo'):
                data['logo'] = request.build_absolute_uri(instance.logo.url)
        return data

class SponsorApplicationSerializer(ModelSerializer):
    event_details = serializers.SerializerMethodField()

    class Meta:
        model = SponsorApplication
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at']

    def get_event_details(self, obj):
        events = obj.events.all()
        return [{'id': e.id, 'name': e.name, 'event_date': e.event_date} for e in events]

    def create(self, validated_data):
        events_data = validated_data.pop('events', [])
        application = SponsorApplication.objects.create(**validated_data)
        if events_data:
            application.events.set(events_data)
        return application


class SponsorshipNegotiationSerializer(ModelSerializer):
    class Meta:
        model = SponsorshipNegotiation
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class EventSponsorshipApprovalSerializer(ModelSerializer):
    class Meta:
        model = EventSponsorshipApproval
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorshipCertificateSerializer(ModelSerializer):
    class Meta:
        model = EventSponsorshipCertificate
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorshipContractSerializer(ModelSerializer):
    class Meta:
        model = EventSponsorshipContract
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorshipDowngradeSerializer(ModelSerializer):
    class Meta:
        model = EventSponsorshipDowngrade
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorshipExtensionSerializer(ModelSerializer):
    class Meta:
        model = EventSponsorshipExtension
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorshipFeedbackSerializer(ModelSerializer):
    class Meta:
        model = EventSponsorshipFeedback
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorshipEvaluationSerializer(ModelSerializer):
    class Meta:
        model = EventSponsorshipEvaluation
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorshipInvoiceSerializer(ModelSerializer):
    class Meta:
        model = EventSponsorshipInvoice
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorshipLetterSerializer(ModelSerializer):
    class Meta:
        model = EventSponsorshipLetter
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorshipHistorySerializer(ModelSerializer):
    class Meta:
        model = EventSponsorshipHistory
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorshipLevelSerializer(ModelSerializer):
    class Meta:
        model = EventSponsorshipLevel
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorshipRecognitionSerializer(ModelSerializer):
    class Meta:
        model = EventSponsorshipRecognition
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorshipRenewalSerializer(ModelSerializer):
    class Meta:
        model = EventSponsorshipRenewal
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorshipReportSerializer(ModelSerializer):
    class Meta:
        model = EventSponsorshipReport
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorshipTerminationSerializer(ModelSerializer):
    class Meta:
        model = EventSponsorshipTermination
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorshipTransferSerializer(ModelSerializer):
    class Meta:
        model = EventSponsorshipTransfer
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorshipUpgradeSerializer(ModelSerializer):
    class Meta:
        model = EventSponsorshipUpgrade
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSurveySerializer(ModelSerializer):
    questions = serializers.SerializerMethodField()

    class Meta:
        model = EventSurvey
        fields = '__all__'

    def get_questions(self, obj):
        questions = EventSurveyQuestion.objects.filter(survey=obj)
        return EventSurveyQuestionSerializer(questions, many=True).data

class EventSurveyQuestionSerializer(ModelSerializer):
    response_count = serializers.SerializerMethodField()

    class Meta:
        model = EventSurveyQuestion
        fields = '__all__'

    def get_response_count(self, obj):
        return EventSurveyResponse.objects.filter(question=obj).count()

class EventSurveyResponseSerializer(ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()

    class Meta:
        model = EventSurveyResponse
        fields = '__all__'

    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email

    def get_user_email(self, obj):
        return obj.user.email

class EventTagSerializer(ModelSerializer):
    class Meta:
        model = EventTag
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventTicketSerializer(ModelSerializer):
    class Meta:
        model = EventTicket
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventTagAssignmentSerializer(ModelSerializer):
    class Meta:
        model = EventTagAssignment
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventVideoSerializer(ModelSerializer):
    class Meta:
        model = EventVideo
        fields = '__all__'
        read_only_fields = ['timestamp']


class EventReportSerializer(ModelSerializer):
    class Meta:
        model = EventReport
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventInvitationSerializer(ModelSerializer):
    class Meta:
        model = EventInvitation
        fields = '__all__'
        read_only_fields = ['timestamp']


class EventSlotBookingSerializer(ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()
    event_name = serializers.SerializerMethodField()
    event_date = serializers.SerializerMethodField()
    event_location = serializers.SerializerMethodField()
    event_organizer = serializers.SerializerMethodField()

    class Meta:
        model = EventSlotBooking
        fields = '__all__'
        read_only_fields = ['booked_at', 'ticket_number', 'qr_code_data', 'uuid']

    def get_user_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email
        return 'Guest'

    def get_user_email(self, obj):
        return obj.user.email if obj.user else ''

    def get_event_name(self, obj):
        return obj.event.name if obj.event else ''

    def get_event_date(self, obj):
        if obj.event:
            return str(obj.event.event_date)
        return ''

    def get_event_location(self, obj):
        return obj.event.location if obj.event else ''

    def get_event_organizer(self, obj):
        if obj.event and obj.event.created_by:
            return f"{obj.event.created_by.first_name} {obj.event.created_by.last_name}".strip() or obj.event.created_by.email
        if obj.event and obj.event.organisation:
            return obj.event.organisation.name
        return 'Qomrade'


class OrganizerFollowSerializer(ModelSerializer):
    class Meta:
        model = OrganizerFollow
        fields = '__all__'
        read_only_fields = ['follower', 'created_at']

class SponsorFollowSerializer(ModelSerializer):
    class Meta:
        model = SponsorFollow
        fields = '__all__'
        read_only_fields = ['follower', 'created_at']

class PartnershipInvitationSerializer(ModelSerializer):
    class Meta:
        model = PartnershipInvitation
        fields = '__all__'
        read_only_fields = ['sender', 'created_at', 'updated_at']

class CoOrganizerSerializer(ModelSerializer):
    class Meta:
        model = CoOrganizer
        fields = '__all__'
        read_only_fields = ['added_by', 'created_at']


# class EventScheduler(Serializer):
#     event_id = serializers.ModelField(Event)
#     scheduled
