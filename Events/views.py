from django.shortcuts import render
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ModelViewSet
from Events.serializers import EventSerializer
from Events.models import Event, EventCategory, EventAttendance, EventBudget, EventCategoryAssignment, EventCollaboration, EventFeedback, EventFeedbackResponse, EventFile, EventFollowUp, EventLogistics, EventMediaCoverage, EventPartnership, EventPhoto, EventPromotion, EventRegistration, EventReminder, EventSchedule, EventSession, EventSpeaker, EventSponsor, EventSponsorAgreement, EventSponsorBenefit, EventSponsorLogo, EventSponsorPackage, EventSponsorPayment, EventSponsorshipAgreementDocument, EventSponsorshipApplication, EventSponsorshipApproval, EventSponsorshipCertificate, EventSponsorshipContract, EventSponsorshipDowngrade, EventSponsorshipEvaluation, EventSponsorshipExtension, EventSponsorshipFeedback, EventSponsorshipHistory, EventSponsorshipInvoice, EventSponsorshipLetter, EventSponsorshipLevel, EventSponsorshipRecognition, EventSponsorshipRejection, EventSponsorshipRenewal, EventSponsorshipReport, EventSponsorshipTermination, EventSponsorshipTransfer, EventSponsorshipUpgrade, EventSurvey, EventSurveyQuestion, EventSurveyResponse, EventTag, EventTagAssignment, EventTicket, EventVideo
from Events.serializers import EventSerializer, EventCategorySerializer, EventAttendanceSerializer, EventBudgetSerializer, EventCategoryAssignmentSerializer, EventCollaborationSerializer, EventFeedbackSerializer, EventFeedbackResponseSerializer, EventFileSerializer, EventFollowUpSerializer, EventLogisticsSerializer, EventMediaCoverageSerializer, EventPartnershipSerializer, EventPhotoSerializer, EventPromotionSerializer, EventRegistrationSerializer, EventReminderSerializer, EventScheduleSerializer, EventSessionSerializer, EventSpeakerSerializer, EventSponsorSerializer, EventSponsorAgreementSerializer, EventSponsorBenefitSerializer, EventSponsorLogoSerializer, EventSponsorPackageSerializer, EventSponsorPaymentSerializer, EventSponsorshipAgreementDocumentSerializer, EventSponsorshipApplicationSerializer, EventSponsorshipApprovalSerializer, EventSponsorshipCertificateSerializer, EventSponsorshipContractSerializer, EventSponsorshipDowngradeSerializer, EventSponsorshipEvaluationSerializer, EventSponsorshipExtensionSerializer, EventSponsorshipFeedbackSerializer, EventSponsorshipHistorySerializer, EventSponsorshipInvoiceSerializer, EventSponsorshipLetterSerializer, EventSponsorshipLevelSerializer, EventSponsorshipRecognitionSerializer, EventSponsorshipRejectionSerializer, EventSponsorshipRenewalSerializer, EventSponsorshipReportSerializer, EventSponsorshipTerminationSerializer, EventSponsorshipTransferSerializer, EventSponsorshipUpgradeSerializer, EventSurveySerializer, EventSurveyQuestionSerializer, EventSurveyResponseSerializer, EventTagSerializer, EventTagAssignmentSerializer, EventTicketSerializer, EventVideoSerializer
# Create your views here.


class EventViewSet(ModelViewSet):
    serializer_class = EventSerializer
    queryset = Event.objects.all()
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
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventCollaborationViewSet(ModelViewSet):
    serializer_class = EventCollaborationSerializer
    queryset = EventCollaboration.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

class EventFileViewSet(ModelViewSet):
    serializer_class = EventFileSerializer
    queryset = EventFile.objects.all()
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

class EventReminderViewSet(ModelViewSet):
    serializer_class = EventReminderSerializer
    queryset = EventReminder.objects.all()
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

