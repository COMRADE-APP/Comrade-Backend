from Events.models import Event, EventCategory, EventAttendance, EventBudget, EventCategoryAssignment, EventCollaboration, EventFeedback, EventFeedbackResponse, EventFile, EventFollowUp, EventLogistics, EventMediaCoverage, EventPartnership, EventPhoto, EventPromotion, EventRegistration, EventReminder, EventSchedule, EventSession, EventSpeaker, EventSponsor, EventSponsorAgreement, EventSponsorBenefit, EventSponsorLogo, EventSponsorPackage, EventSponsorPayment, EventSponsorshipAgreementDocument, EventSponsorshipApplication, EventSponsorshipApproval, EventSponsorshipCertificate, EventSponsorshipContract, EventSponsorshipDowngrade, EventSponsorshipEvaluation, EventSponsorshipExtension, EventSponsorshipFeedback, EventSponsorshipHistory, EventSponsorshipInvoice, EventSponsorshipLetter, EventSponsorshipLevel, EventSponsorshipRecognition, EventSponsorshipRejection, EventSponsorshipRenewal, EventSponsorshipReport, EventSponsorshipTermination, EventSponsorshipTransfer, EventSponsorshipUpgrade, EventSurvey, EventSurveyQuestion, EventSurveyResponse, EventTag, EventTagAssignment, EventTicket, EventVideo, EventReport, EventInvitation, EventLike, EventVisibility, VisibilityLog
from rest_framework.serializers import ModelSerializer, Serializer
from rest_framework import serializers
from datetime import datetime

class EventSerializer(ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = '__all__'
        read_only_fields = ['time_stamp', 'created_by']

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.email
        return None

    def validate_event_date(self, value):
        from django.utils import timezone
        if value < timezone.now():
            raise serializers.ValidationError("Event date cannot be in the past.")
        return value

    def validate_scheduled_time(self, value):
        if value < datetime.now():
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
    class Meta:
        model = EventAttendance
        fields = '__all__'
        read_only_fields = ['timestamp']

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
    class Meta:
        model = EventFeedback
        fields = '__all__'
        read_only_fields = ['timestamp']

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
    class Meta:
        model = EventSponsorshipApplication
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSponsorshipApplicationSerializer(ModelSerializer):
    class Meta:
        model = EventSponsorshipApplication
        fields = '__all__'
        read_only_fields = ['timestamp']

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
    class Meta:
        model = EventSurvey
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSurveyQuestionSerializer(ModelSerializer):
    class Meta:
        model = EventSurveyQuestion
        fields = '__all__'
        read_only_fields = ['timestamp']

class EventSurveyResponseSerializer(ModelSerializer):
    class Meta:
        model = EventSurveyResponse
        fields = '__all__'
        read_only_fields = ['timestamp']

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


# class EventScheduler(Serializer):
#     event_id = serializers.ModelField(Event)
#     scheduled 
