from django.db import models

# Create your models here.
class Event(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(max_length=2000)
    date = models.DateTimeField()
    location = models.CharField(max_length=300)

    def __str__(self):
        return self.name
class EventRegistration(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.CharField(max_length=200)
    registration_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.event.name}"
class EventFeedback(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.CharField(max_length=200)
    feedback = models.TextField(max_length=2000)
    rating = models.IntegerField()

    def __str__(self):
        return f"{self.user} - {self.event.name} - {self.rating}"
class EventSponsor(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    sponsor_name = models.CharField(max_length=200)
    sponsor_details = models.TextField(max_length=1000)

    def __str__(self):
        return f"{self.sponsor_name} - {self.event.name}"
class EventSchedule(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    activity_name = models.CharField(max_length=200)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    def __str__(self):
        return f"{self.activity_name} - {self.event.name}"
class EventSpeaker(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    speaker_name = models.CharField(max_length=200)
    speaker_bio = models.TextField(max_length=1000)

    def __str__(self):
        return f"{self.speaker_name} - {self.event.name}"
class EventTicket(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    ticket_type = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_available = models.IntegerField()

    def __str__(self):
        return f"{self.ticket_type} - {self.event.name}"
class EventOrganizer(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    organizer_name = models.CharField(max_length=200)
    organizer_contact = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.organizer_name} - {self.event.name}"
class EventPhoto(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    photo = models.ImageField(upload_to='event_photos/')
    description = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return f"Photo for {self.event.name}"
    
class EventVideo(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    video = models.FileField(upload_to='event_videos/')
    description = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return f"Video for {self.event.name}"
    
class EventSponsorPackage(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    package_name = models.CharField(max_length=200)
    package_details = models.TextField(max_length=1000)
    package_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.package_name} - {self.event.name}"
    
class EventVolunteer(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    volunteer_name = models.CharField(max_length=200)
    volunteer_contact = models.CharField(max_length=200)
    assigned_role = models.CharField(max_length=300)

    def __str__(self):
        return f"{self.volunteer_name} - {self.event.name}"
class EventAnnouncement(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    message = models.TextField(max_length=2000)
    announcement_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.event.name}"
class EventSponsorContact(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    sponsor_name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=200)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.sponsor_name} Contact - {self.event.name}"
class EventLogistics(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    item_name = models.CharField(max_length=200)
    quantity = models.IntegerField()
    supplier = models.CharField(max_length=200)
    delivery_date = models.DateTimeField()

    def __str__(self):
        return f"{self.item_name} - {self.event.name}"
class EventBudget(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    item_description = models.CharField(max_length=300)
    amount_allocated = models.DecimalField(max_digits=10, decimal_places=2)
    amount_spent = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.item_description} - {self.event.name}"
class EventSponsorAgreement(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    sponsor_name = models.CharField(max_length=200)
    agreement_details = models.TextField(max_length=2000)
    signed_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sponsor_name} Agreement - {self.event.name}"
class EventFeedbackResponse(models.Model):
    feedback = models.ForeignKey(EventFeedback, on_delete=models.CASCADE)
    response_message = models.TextField(max_length=2000)
    response_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Response to {self.feedback.user} - {self.feedback.event.name}"
class EventReminder(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    reminder_message = models.CharField(max_length=300)
    reminder_date = models.DateTimeField()

    def __str__(self):
        return f"Reminder for {self.event.name}"
class EventCategory(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(max_length=1000)

    def __str__(self):
        return self.name
class EventTag(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
class EventCategoryAssignment(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    category = models.ForeignKey(EventCategory, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.event.name} - {self.category.name}"
class EventTagAssignment(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    tag = models.ForeignKey(EventTag, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.event.name} - {self.tag.name}"
class EventSession(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    session_name = models.CharField(max_length=200)
    speaker = models.CharField(max_length=200)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    def __str__(self):
        return f"{self.session_name} - {self.event.name}"
class EventSponsorContactPerson(models.Model):
    sponsor = models.ForeignKey(EventSponsor, on_delete=models.CASCADE)
    contact_person_name = models.CharField(max_length=200)
    contact_person_email = models.EmailField()
    contact_person_phone = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.contact_person_name} - {self.sponsor.sponsor_name}"
class EventAttendance(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.CharField(max_length=200)
    check_in_time = models.DateTimeField(auto_now_add=True)
    check_out_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} - {self.event.name}"
class EventSponsorBenefit(models.Model):
    sponsor = models.ForeignKey(EventSponsor, on_delete=models.CASCADE)
    benefit_description = models.TextField(max_length=1000)

    def __str__(self):
        return f"Benefit for {self.sponsor.sponsor_name}"
class EventSurvey(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    survey_title = models.CharField(max_length=200)
    survey_description = models.TextField(max_length=2000)

    def __str__(self):
        return f"{self.survey_title} - {self.event.name}"
class EventSurveyQuestion(models.Model):
    survey = models.ForeignKey(EventSurvey, on_delete=models.CASCADE)
    question_text = models.TextField(max_length=1000)

    def __str__(self):
        return f"Question for {self.survey.survey_title}"
class EventSurveyResponse(models.Model):
    question = models.ForeignKey(EventSurveyQuestion, on_delete=models.CASCADE)
    user = models.CharField(max_length=200)
    response_text = models.TextField(max_length=2000)

    def __str__(self):
        return f"Response by {self.user} to {self.question.survey.survey_title}"
class EventSponsorLogo(models.Model):
    sponsor = models.ForeignKey(EventSponsor, on_delete=models.CASCADE)
    logo = models.ImageField(upload_to='sponsor_logos/')

    def __str__(self):
        return f"Logo for {self.sponsor.sponsor_name}"
class EventPromotion(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    promotion_channel = models.CharField(max_length=200)
    promotion_details = models.TextField(max_length=1000)

    def __str__(self):
        return f"Promotion for {self.event.name} via {self.promotion_channel}"
class EventMediaCoverage(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    media_outlet = models.CharField(max_length=200)
    coverage_details = models.TextField(max_length=2000)

    def __str__(self):
        return f"Media Coverage for {self.event.name} by {self.media_outlet}"
class EventSponsorPayment(models.Model):
    sponsor = models.ForeignKey(EventSponsor, on_delete=models.CASCADE)
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment by {self.sponsor.sponsor_name}"
class EventFollowUp(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    follow_up_message = models.TextField(max_length=2000)
    follow_up_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Follow Up for {self.event.name}"
class EventCollaboration(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    collaborator_name = models.CharField(max_length=200)
    collaboration_details = models.TextField(max_length=1000)

    def __str__(self):
        return f"Collaboration with {self.collaborator_name} for {self.event.name}"
class EventPartnership(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    partner_name = models.CharField(max_length=200)
    partnership_details = models.TextField(max_length=1000)

    def __str__(self):
        return f"Partnership with {self.partner_name} for {self.event.name}"
class EventSponsorshipLevel(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    level_name = models.CharField(max_length=200)
    level_benefits = models.TextField(max_length=1000)
    level_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.level_name} - {self.event.name}"
class EventSponsorshipApplication(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    applicant_name = models.CharField(max_length=200)
    applicant_contact = models.CharField(max_length=200)
    application_details = models.TextField(max_length=2000)

    def __str__(self):
        return f"Application by {self.applicant_name} for {self.event.name}"
class EventSponsorshipApproval(models.Model):
    application = models.ForeignKey(EventSponsorshipApplication, on_delete=models.CASCADE)
    approval_status = models.CharField(max_length=100)
    approval_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Approval for {self.application.applicant_name} - {self.approval_status}"
class EventSponsorshipRejection(models.Model):
    application = models.ForeignKey(EventSponsorshipApplication, on_delete=models.CASCADE)
    rejection_reason = models.TextField(max_length=2000)
    rejection_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rejection for {self.application.applicant_name}" - {self.rejection_reason}"
class EventSponsorshipRenewal(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.CASCADE)
    renewal_date = models.DateTimeField(auto_now_add=True)
    renewal_details = models.TextField(max_length=2000)

    def __str__(self):
        return f"Renewal for {self.sponsorship.sponsor_name}"
class EventSponsorshipTermination(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.CASCADE)
    termination_date = models.DateTimeField(auto_now_add=True)
    termination_reason = models.TextField(max_length=2000)

    def __str__(self):
        return f"Termination for {self.sponsorship.sponsor_name}"
class EventSponsorshipExtension(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.CASCADE)
    extension_date = models.DateTimeField(auto_now_add=True)
    extension_details = models.TextField(max_length=2000)

    def __str__(self):
        return f"Extension for {self.sponsorship.sponsor_name}"
class EventSponsorshipUpgrade(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.CASCADE)
    upgrade_date = models.DateTimeField(auto_now_add=True)
    upgrade_details = models.TextField(max_length=2000)

    def __str__(self):
        return f"Upgrade for {self.sponsorship.sponsor_name}"
class EventSponsorshipDowngrade(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.CASCADE)
    downgrade_date = models.DateTimeField(auto_now_add=True)
    downgrade_details = models.TextField(max_length=2000)

    def __str__(self):
        return f"Downgrade for {self.sponsorship.sponsor_name}"
class EventSponsorshipTransfer(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.CASCADE)
    transfer_date = models.DateTimeField(auto_now_add=True)
    new_sponsor_name = models.CharField(max_length=200)

    def __str__(self):
        return f"Transfer of {self.sponsorship.sponsor_name} to {self.new_sponsor_name}"
class EventSponsorshipHistory(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.CASCADE)
    change_date = models.DateTimeField(auto_now_add=True)
    change_details = models.TextField(max_length=2000)

    def __str__(self):
        return f"History for {self.sponsorship.sponsor_name} - {self.change_date}"
class EventSponsorshipReport(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.CASCADE)
    report_date = models.DateTimeField(auto_now_add=True)
    report_details = models.TextField(max_length=2000)

    def __str__(self):
        return f"Report for {self.sponsorship.sponsor_name} - {self.report_date}"
class EventSponsorshipFeedback(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.CASCADE)
    feedback_message = models.TextField(max_length=2000)
    feedback_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for {self.sponsorship.sponsor_name} - {self.feedback_date}"
class EventSponsorshipEvaluation(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.CASCADE)
    evaluation_date = models.DateTimeField(auto_now_add=True)
    evaluation_details = models.TextField(max_length=2000)

    def __str__(self):
        return f"Evaluation for {self.sponsorship.sponsor_name} - {self.evaluation_date}"
class EventSponsorshipRecognition(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.CASCADE)
    recognition_date = models.DateTimeField(auto_now_add=True)
    recognition_details = models.TextField(max_length=2000)

    def __str__(self):
        return f"Recognition for {self.sponsorship.sponsor_name} - {self.recognition_date}"
class EventSponsorshipCertificate(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.CASCADE)
    certificate_file = models.FileField(upload_to='sponsorship_certificates/')
    issued_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Certificate for {self.sponsorship.sponsor_name} - {self.issued_date}"
class EventSponsorshipInvoice(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.CASCADE)
    invoice_file = models.FileField(upload_to='sponsorship_invoices/')
    issued_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invoice for {self.sponsorship.sponsor_name} - {self.issued_date}"
class EventSponsorshipContract(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.CASCADE)
    contract_file = models.FileField(upload_to='sponsorship_contracts/')
    signed_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Contract for {self.sponsorship.sponsor_name} - {self.signed_date}"
class EventSponsorshipLetter(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.CASCADE)
    letter_file = models.FileField(upload_to='sponsorship_letters/')
    issued_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Letter for {self.sponsorship.sponsor_name} - {self.issued_date}"
class EventSponsorshipAgreementDocument(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.CASCADE)
    document_file = models.FileField(upload_to='sponsorship_documents/')
    uploaded_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document for {self.sponsorship.sponsor_name} - {self.uploaded_date}"
class EventSponsorshipContactInfo(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.CASCADE)
    contact_name = models.CharField(max_length=200)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)

    def __str__(self):
        return f"Contact for {self.sponsorship.sponsor_name} - {self.contact_name}"
class EventSponsorshipCoordinator(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.CASCADE)
    coordinator_name = models.CharField(max_length=200)
    coordinator_email = models.EmailField()
    coordinator_phone = models.CharField(max_length=20)

    def __str__(self):
        return f"Coordinator for {self.sponsorship.sponsor_name} - {self.coordinator_name}"
class EventSponsorshipManager(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.CASCADE)
    manager_name = models.CharField(max_length=200)
    manager_email = models.EmailField()
    manager_phone = models.CharField(max_length=20)

    def __str__(self):
        return f"Manager for {self.sponsorship.sponsor_name} - {self.manager_name}"
class EventSponsorshipDirector(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.CASCADE)
    director_name = models.CharField(max_length=200)
    director_email = models.EmailField()
    director_phone = models.CharField(max_length=20)

    def __str__(self):
        return f"Director for {self.sponsorship.sponsor_name} - {self.director_name}"
class EventSponsorshipExecutive(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.CASCADE)
    executive_name = models.CharField(max_length=200)
    executive_email = models.EmailField()
    executive_phone = models.CharField(max_length=20)

    def __str__(self):
        return f"Executive for {self.sponsorship.sponsor_name} - {self.executive_name}"
class EventSponsorshipTeamMember(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.CASCADE)
    team_member_name = models.CharField(max_length=200)
    team_member_email = models.EmailField()
    team_member_phone = models.CharField(max_length=20)

    def __str__(self):
        return f"Team Member for {self.sponsorship.sponsor_name} - {self.team_member_name}"
class EventSponsorshipContactPersonRole(models.Model):
    contact_person = models.ForeignKey(EventSponsorshipContactInfo, on_delete=models.CASCADE)
    role_name = models.CharField(max_length=200)
    role_description = models.TextField(max_length=1000)

    def __str__(self):
        return f"Role {self.role_name} for {self.contact_person.contact_name}"


