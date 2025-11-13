from Events.views import EventViewSet, EventCategoryViewSet, EventAttendanceViewSet, EventBudgetViewSet, EventCategoryAssignmentViewSet, EventCollaborationViewSet, EventFeedbackViewSet, EventFeedbackResponseViewSet, EventFileViewSet, EventFollowUpViewSet, EventLogisticsViewSet, EventMediaCoverageViewSet, EventPartnershipViewSet, EventPhotoViewSet, EventPromotionViewSet, EventRegistrationViewSet, EventReminderViewSet, EventScheduleViewSet, EventSessionViewSet, EventSpeakerViewSet, EventSponsorViewSet, EventSponsorAgreementViewSet, EventSponsorBenefitViewSet, EventSponsorLogoViewSet, EventSponsorPackageViewSet, EventSponsorPaymentViewSet, EventSponsorshipAgreementDocumentViewSet, EventSponsorshipApplicationViewSet, EventSponsorshipApprovalViewSet, EventSponsorshipCertificateViewSet, EventSponsorshipContractViewSet, EventSponsorshipDowngradeViewSet, EventSponsorshipEvaluationViewSet, EventSponsorshipExtensionViewSet, EventSponsorshipFeedbackViewSet, EventSponsorshipHistoryViewSet, EventSponsorshipInvoiceViewSet, EventSponsorshipLetterViewSet, EventSponsorshipLevelViewSet, EventSponsorshipRecognitionViewSet, EventSponsorshipRejectionViewSet, EventSponsorshipRenewalViewSet, EventSponsorshipReportViewSet, EventSponsorshipTerminationViewSet, EventSponsorshipTransferViewSet, EventSponsorshipUpgradeViewSet, EventSurveyViewSet, EventSurveyQuestionViewSet, EventSurveyResponseViewSet, EventTagViewSet, EventTagAssignmentViewSet, EventTicketViewSet, EventVideoViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r'event', EventViewSet, basename='event')
router.register(r'event_category', EventCategoryViewSet, basename='event_category')
router.register(r'event_attendance', EventAttendanceViewSet, basename='event_attendance')
router.register(r'event_budget', EventBudgetViewSet, basename='event_budget')
router.register(r'event_cat_assignment', EventCategoryAssignmentViewSet, basename='event_cat_assignment')
router.register(r'event_collaboration', EventCollaborationViewSet, basename='event_collaboration')
router.register(r'event_feedback', EventFeedbackViewSet, basename='event_feedback')
router.register(r'event_feedback_response', EventFeedbackResponseViewSet, basename='event_feedback_response')
router.register(r'event_file', EventFileViewSet, basename='event_file')
router.register(r'event_follow_up', EventFollowUpViewSet, basename='event_follow_up')
router.register(r'event_logistics', EventLogisticsViewSet, basename='event_logistics')
router.register(r'event_media_coverage', EventMediaCoverageViewSet, basename='event_media_coverage')
router.register(r'event_partnership', EventPartnershipViewSet, basename='event_partnership')
router.register(r'event_photo', EventPhotoViewSet, basename='event_photo')
router.register(r'event_promotion', EventPromotionViewSet, basename='event_promotion')
router.register(r'event_reminder', EventReminderViewSet, basename='event_reminder')
router.register(r'event_registration', EventRegistrationViewSet, basename='event_registration')
router.register(r'event_schedule', EventScheduleViewSet, basename='event_schedule')
router.register(r'event_session', EventSessionViewSet, basename='event_session')
router.register(r'event_speaker', EventSpeakerViewSet, basename='event_speaker')
router.register(r'event_sponsor_agreement', EventSponsorAgreementViewSet, basename='event_sponsor_agreement')
router.register(r'event_sponsor_benefit', EventSponsorBenefitViewSet, basename='event_sponsor_benefit')
router.register(r'event_sponsor_logo', EventSponsorLogoViewSet, basename='event_sponsor_logo')
router.register(r'event_sponsor_package', EventSponsorPackageViewSet, basename='event_sponsor_package')
router.register(r'event_sponsor_payment', EventSponsorPaymentViewSet, basename='event_sponsor_payment')
router.register(r'event_sponsorship_agreement_doc', EventSponsorshipAgreementDocumentViewSet, basename='event_sponsorship_agreement_doc')
router.register(r'event_sponsorship_application', EventSponsorshipApplicationViewSet, basename='event_sponsorship_application')
router.register(r'event_sponsorship_approval', EventSponsorshipApprovalViewSet, basename='event_sponsorship_approval')
router.register(r'event_sponsorship_certificate', EventSponsorshipCertificateViewSet, basename='event_sponsorship_certificate')
router.register(r'event_sponsorship_contract', EventSponsorshipContractViewSet, basename='event_sponsorship_contract')
router.register(r'event_sponsorship_downgrade', EventSponsorshipDowngradeViewSet, basename='event_sponsorship_downgrade')
router.register(r'event_sponsorship_evaluation', EventSponsorshipEvaluationViewSet, basename='event_sponsorship_evaluation')
router.register(r'event_sponsorship_extension', EventSponsorshipExtensionViewSet, basename='event_sponsorship_extension')
router.register(r'event_sponsorship_feedback', EventSponsorshipFeedbackViewSet, basename='event_sponsorship_feedback')
router.register(r'event_sponsorship_history', EventSponsorshipHistoryViewSet, basename='event_sponsorship_history')
router.register(r'event_sponsorship_invoice', EventSponsorshipInvoiceViewSet, basename='event_sponsorship_invoice')
router.register(r'event_sponsorship_letter', EventSponsorshipLetterViewSet, basename='event_sponsorship_letter')
router.register(r'event_sponsorship_level', EventSponsorshipLevelViewSet, basename='event_sponsorship_level')
router.register(r'event_sponsorship_recognition', EventSponsorshipRecognitionViewSet, basename='event_sponsorship_recognition')
router.register(r'event_sponsorship_rejection', EventSponsorshipRejectionViewSet, basename='event_sponsorship_rejection')
router.register(r'event_sponsorship_renewal', EventSponsorshipRenewalViewSet, basename='event_sponsorship_renewal')
router.register(r'event_sponsorship_report', EventSponsorshipReportViewSet, basename='event_sponsorship_report')
router.register(r'event_sponsorship_termination', EventSponsorshipTerminationViewSet, basename='event_sponsorship_termination')
router.register(r'event_sponsorship_transfer', EventSponsorshipTransferViewSet, basename='event_sponsorship_transfer')
router.register(r'event_sponsorship_upgrade', EventSponsorshipUpgradeViewSet, basename='event_sponsorship_upgrade')
router.register(r'event_survey', EventSurveyViewSet, basename='event_survey')
router.register(r'event_survey_question', EventSurveyQuestionViewSet, basename='event_survey_question')
router.register(r'event_survey_response', EventSurveyResponseViewSet, basename='event_survey_response')
router.register(r'event_tag', EventTagViewSet, basename='event_tag')
router.register(r'event_tag_assignment', EventTagAssignmentViewSet, basename='event_tag_assignment')
router.register(r'event_ticket', EventTicketViewSet, basename='event_ticket')
router.register(r'event_video', EventVideoViewSet, basename='event_video')



url_patterns = [

]
url_patterns += router.urls 


