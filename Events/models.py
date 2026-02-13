from django.db import models
from Authentication.models import Student, StudentAdmin, OrgAdmin, OrgStaff, InstAdmin, InstStaff, Lecturer, CustomUser, Profile
from Organisation.models import Organisation, OrgBranch, Division, Department, Section, Team, Project, Centre, Committee, Board, Unit, Institute, Program, OtherOrgUnit
from Institution.models import Institution, InstBranch, Faculty, VCOffice, InstDepartment, AdminDep, Programme, HR, Admissions, HealthServices, Security, StudentAffairs, SupportServices, Finance, Marketing, Legal, ICT, CareerOffice, Counselling, RegistrarOffice, Transport, Library, Hostel, Cafeteria, OtherInstitutionUnit
# from Resources.models import Resource

from datetime import datetime, timezone

# Create your models here.
EVENT_STATE = (
    ('active', 'Active'),
    ('live', 'live'),
    ('inactive', 'Inactive'),
    ('cancelled', 'Cancelled'),
    ('postponed', 'Postponed'),
    ('deleted', 'Deleted'),
    ('draft', 'Draft'),
    ('archived', 'Archived'),
    ('upcoming', 'Upcoming'),
    ('scheduled', 'Scheduled'),
    ('completed', 'Completed'),
    ('ongoing', 'Ongoing'),
)

BOOKING_STATE = (
    ('open', 'Open'),
    ('closed', 'Closed'),
    ('pending', 'Pending')
)

ATTENDEE_STATUS = (
    ('attendee', 'Attendee'),
    ('host', 'Host'),
    ('guest_speaker', 'Guest Speaker'),
    ('main_speaker', 'Main Speaker'),
    ('sponsor_rep', 'Sponsor\'s Representative'),
    ('patner_rep', 'Patner\'s Representative'),
    ('collaborator_rep', 'Collaborator\'s Representative'),
    ('coordinator', 'Coordinator'),
    ('moderator', 'Moderator'),
    ('organiser', 'Organiser'),
    ('volunteer', 'Volunteer')
)

TICKET_TYPE = (
    ('regular', 'Regular Tickets'),
    ('vip', 'VIP Tickets'),
    ('vvip', 'VVIP Tickets'),
    ('couple', 'Couple Tickets'),
    ('group', 'Group Tickets')
)

APPROVAL_PERM = (
    ('pending', 'Pending Approval'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('on_review', 'On Reveiwal Stage'),
    ('disqualified', 'Disqualified'),
    ('inactive', 'Inactive'),
    ('renewed', 'Renewed'),
    ('extended', 'Extended'),
    ('upgraded', 'Upgraded'),
    ('downgraded', 'Downgraded'),
    ('transferred', 'Transferred'),
)

ATTEND_STATE = (
    ('interested', 'Interested'),
    ('bookmarked', 'Bookmarked'),
    ('attending', 'Attending'),
    ('at_the_event', 'Currently at the Event'),
    ('attended', 'Attended'),
    ('missed', 'Missed'),
    ('cancelled', 'Cancelled on Attending'),
    ('blocked', 'Blocked'),
    ('disliked', 'Disliked'),
    ('report', 'Report'),
    ('neutral', 'Neutral')
)

EVENT_TYPE = (
    ('public', 'Public'),
    ('private', 'Private'),
    ('invite_only', 'Invite Only'),
    ('members_only', 'Members Only'),
    ('students_only', 'Students Only'),
    ('staff_only', 'Staff Only'),
    ('faculty_only', 'Faculty Only'),
    ('department_only', 'Department Only'),
    ('division_only', 'Division Only'),
    ('organisation_only', 'Organisation Only'),
    ('institution_only', 'Institution Only'),
    ('program_only', 'Program Only'),
    ('other_organisation_unit_only', 'Other Organisation Unit Only'),
    ('other_institution_unit_only', 'Other Institution Unit Only'),
)

EVENT_LOCATION = (
    ('online', 'Online'),
    ('physical', 'Physical'),
    ('hybrid', 'Hybrid'),
)


class Event(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(max_length=2000)
    capacity = models.IntegerField()
    duration = models.DurationField()
    event_type = models.CharField(max_length=200, choices=EVENT_TYPE, default='public')
    event_location = models.CharField(max_length=200, choices=EVENT_LOCATION, default='physical')
    event_url = models.URLField(blank=True, null=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    booking_deadline = models.DateTimeField(default=datetime.now)
    booking_status = models.CharField(max_length=200, choices=BOOKING_STATE, default='pending')
    attendees = models.ManyToManyField(CustomUser, blank=True, related_name='event_attendees')
    attendees_viewable = models.BooleanField(default=False)
    activate_feedback = models.BooleanField(default=True)
    event_date = models.DateTimeField(default=datetime.now)
    deadline_reached = models.BooleanField(default=False)
    location = models.CharField(max_length=300)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    complexity_level = models.CharField(max_length=50, choices=(
        ('small', 'Small Event'),
        ('midlevel', 'Mid-Level Event'),
        ('sophisticated', 'Sophisticated Event'),
    ), default='small')
    status = models.CharField(max_length=200, choices=EVENT_STATE, default='active')
    scheduled_time = models.DateTimeField(default=datetime.now)
    time_stamp = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(CustomUser, null=False, on_delete=models.DO_NOTHING)
    # Entity Authorship
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, null=True, blank=True, related_name='events')
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, null=True, blank=True, related_name='events')

    def __str__(self):
        return self.name
    

class EventVisibility(models.Model):
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='event_visibility')
    scheduled_time = models.DateTimeField(null=True, blank=True)
    expiry_time = models.DateTimeField(null=True, blank=True)
    rooms = models.ManyToManyField('Rooms.Room', blank=True)
    default_rooms = models.ManyToManyField('Rooms.DefaultRoom', blank=True)
    direct_message_rooms = models.ManyToManyField('Rooms.DirectMessageRoom', blank=True)
    organisations = models.ManyToManyField(Organisation, blank=True)
    organistion_branches = models.ManyToManyField(OrgBranch, blank=True)
    divisions = models.ManyToManyField(Division, blank=True)
    departments = models.ManyToManyField(Department, blank=True)
    sections = models.ManyToManyField(Section, blank=True)
    teams = models.ManyToManyField(Team, blank=True)
    projects = models.ManyToManyField(Project, blank=True)
    centres = models.ManyToManyField(Centre, blank=True)
    committees = models.ManyToManyField(Committee, blank=True)
    boards = models.ManyToManyField(Board, blank=True)
    units = models.ManyToManyField(Unit, blank=True)
    institutes = models.ManyToManyField(Institute, blank=True)
    programs = models.ManyToManyField(Program, blank=True)
    other_organisation_units = models.ManyToManyField(OtherOrgUnit, blank=True)
    institutions = models.ManyToManyField(Institution, blank=True)
    institution_branches = models.ManyToManyField(InstBranch, blank=True)
    faculties = models.ManyToManyField(Faculty, blank=True)
    vc_offices = models.ManyToManyField(VCOffice, blank=True)
    inst_departments = models.ManyToManyField(InstDepartment, blank=True)
    admin_deps = models.ManyToManyField(AdminDep, blank=True)
    programmes = models.ManyToManyField(Programme, blank=True)
    hrs = models.ManyToManyField(HR, blank=True)
    admissions = models.ManyToManyField(Admissions, blank=True)
    health_services = models.ManyToManyField(HealthServices, blank=True)
    securities = models.ManyToManyField(Security, blank=True)
    student_affairs = models.ManyToManyField(StudentAffairs, blank=True)
    support_services = models.ManyToManyField(SupportServices, blank=True)
    finances = models.ManyToManyField(Finance, blank=True)
    marketings = models.ManyToManyField(Marketing, blank=True)
    legals = models.ManyToManyField(Legal, blank=True)
    icts = models.ManyToManyField(ICT, blank=True)
    career_offices = models.ManyToManyField(CareerOffice, blank=True)
    counsellings = models.ManyToManyField(Counselling, blank=True)
    registrar_offices = models.ManyToManyField(RegistrarOffice, blank=True)
    transports = models.ManyToManyField(Transport, blank=True)
    libraries = models.ManyToManyField(Library, blank=True)
    hostels = models.ManyToManyField(Hostel, blank=True)
    cafeterias = models.ManyToManyField(Cafeteria, blank=True)
    other_institution_units = models.ManyToManyField(OtherInstitutionUnit, blank=True)
    users_with_access = models.ManyToManyField(Profile, blank=True)

    def __str__(self):
        return f'Visibility for {self.event.name} (Event)'
    
class VisibilityLog(models.Model):
    resource = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='event_visibility_logs')
    changed_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, related_name='event_visibility_changed_logs', null=True)
    previous_visibility = models.ForeignKey(EventVisibility, on_delete=models.SET_NULL, related_name='event_previous_visibility_logs', null=True)
    new_visibility = models.ForeignKey(EventVisibility, on_delete=models.SET_NULL, related_name='event_new_visibility_logs', null=True)
    changed_on = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return f"Visibility change for {self.event.title} by {self.changed_by.username} on {self.changed_on}"


    
class EventRegistration(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    user = models.ForeignKey(CustomUser, null=False, on_delete=models.DO_NOTHING)
    attendee_status = models.CharField(max_length=200, choices=ATTENDEE_STATUS, default='attendee')
    attendance_permission = models.CharField(max_length=200, choices=APPROVAL_PERM, default='pending')
    registration_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.event.name}"
    
class EventLike(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    user = models.ForeignKey(CustomUser, null=False, on_delete=models.DO_NOTHING, related_name='commenter')
    like = models.BooleanField(default=False)
    comment = models.TextField(max_length=2000, null=True)
    reaction = models.CharField(max_length=2000)
    viewable = models.BooleanField(default=True)
    created_on = models.DateTimeField(default=datetime.now)
    
class EventFeedback(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    user = models.ForeignKey(CustomUser, null=False, on_delete=models.DO_NOTHING)
    feedback = models.TextField(max_length=2000, default='')
    rating = models.IntegerField(default=0)
    attendendance_status = models.CharField(max_length=200, choices=ATTEND_STATE, default='neutral')
    viewable = models.BooleanField(default=True)
    submitted_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.event.name} - {self.rating}"
    
class EventInvitation(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    invited_user = models.ForeignKey(CustomUser, null=False, on_delete=models.DO_NOTHING, related_name='invited_user')
    invited_by = models.ForeignKey(CustomUser, null=False, on_delete=models.DO_NOTHING, related_name='inviter_user')
    invitation_message = models.TextField(max_length=1000)
    sent_on = models.DateTimeField(auto_now_add=True)
    response_status = models.CharField(max_length=200, choices=APPROVAL_PERM, default='pending')

    def __str__(self):
        return f"Invitation to {self.invited_user} for {self.event.name}"
    
class EventReport(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    report_title = models.CharField(max_length=200)
    report_content = models.TextField(max_length=5000)
    generated_on = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(CustomUser, null=False, on_delete=models.DO_NOTHING)

    def __str__(self):
        return f"{self.report_title} - {self.event.name}"
    
    
class EventSponsor(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    organisation = models.ForeignKey(Organisation, on_delete=models.DO_NOTHING)
    sponsor_rep = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)
    sponsor_name = models.CharField(max_length=200)
    sponsor_details = models.TextField(max_length=1000)
    established_on = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.sponsor_name} - {self.event.name}"
    
class EventSchedule(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    activity_name = models.CharField(max_length=200)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.activity_name} - {self.event.name}"
    
class EventSession(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    session_name = models.CharField(max_length=200)
    speaker = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    def __str__(self):
        return f"{self.session_name} - {self.event.name}"
    
class EventSpeaker(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    user = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.DO_NOTHING, related_name='speaker_user')
    speaker_name = models.CharField(max_length=200)
    speaker_bio = models.TextField(max_length=1000)
    added_by = models.ForeignKey(CustomUser, null=False, on_delete=models.DO_NOTHING, related_name='moderator_user')
    slotted_schedule = models.ForeignKey(EventSchedule, on_delete=models.DO_NOTHING)

    def __str__(self):
        return f"{self.speaker_name} - {self.event.name}"
    
class EventTicket(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    ticket_type = models.CharField(max_length=100, choices=TICKET_TYPE, default='regular')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_available = models.IntegerField()
    qr_code = models.FileField(upload_to='events_tickets/')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ticket_type} - {self.event.name}"
    
# class EventOrganizer(models.Model):
#     event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
#     organizer_name = models.CharField(max_length=200)
#     organizer_contact = models.CharField(max_length=200)

#     def __str__(self):
#         return f"{self.organizer_name} - {self.event.name}"
    
class EventPhoto(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    photo = models.ImageField(upload_to='event_photos/')
    description = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return f"Photo for {self.event.name}"
    
class EventVideo(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    video = models.FileField(upload_to='event_videos/')
    description = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return f"Video for {self.event.name}"
    
class EventSponsorPackage(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    package_name = models.CharField(max_length=200)
    package_details = models.TextField(max_length=1000)
    package_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.package_name} - {self.event.name}"
    
# class EventVolunteer(models.Model):
#     event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
#     volunteer_name = models.CharField(max_length=200)
#     volunteer_contact = models.CharField(max_length=200)
#     assigned_role = models.CharField(max_length=300)

#     def __str__(self):
#         return f"{self.volunteer_name} - {self.event.name}"
    
# class EventAnnouncement(models.Model):
#     event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
#     title = models.CharField(max_length=200)
#     message = models.TextField(max_length=2000)
#     announcement_date = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.title} - {self.event.name}"
# class EventSponsorContact(models.Model):
#     event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
#     sponsor_name = models.CharField(max_length=200)
#     contact_person = models.CharField(max_length=200)
#     contact_email = models.EmailField()
#     contact_phone = models.CharField(max_length=20)

    # def __str__(self):
    #     return f"{self.sponsor_name} Contact - {self.event.name}"
class EventLogistics(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    item_name = models.CharField(max_length=200)
    description = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    total_spent = models.DecimalField(max_digits=10, decimal_places=2)
    supplier = models.CharField(max_length=200)
    delivery_date = models.DateTimeField()
    approved_by = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)
    approval_status = models.CharField(max_length=200, choices=APPROVAL_PERM, default='pending')

    def __str__(self):
        return f"{self.item_name} - {self.event.name}"
    
class EventBudget(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    item_description = models.CharField(max_length=300)
    amount_allocated = models.DecimalField(max_digits=10, decimal_places=2)
    amount_spent = models.DecimalField(max_digits=10, decimal_places=2)
    decided_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.item_description} - {self.event.name}"
    
class EventFile(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    file_type = models.CharField(max_length=200)
    file_content = models.FileField(upload_to='event_files/')
    description = models.TextField(max_length=5000)
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.file_type} - {self.event.name} - {self.created_on}'
    
class EventSponsorAgreement(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    organisation = models.ForeignKey(Organisation, on_delete=models.DO_NOTHING, null=True, blank=True, related_name='named_sponsor')
    sponsor_name = models.CharField(max_length=200)
    agreement_details = models.TextField(max_length=2000)
    participants = models.ManyToManyField(Organisation, blank=True, related_name='organisations_participating')
    agreement_file = models.ForeignKey(EventFile, on_delete=models.DO_NOTHING)
    signed_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sponsor_name} Agreement - {self.event.name}"

class EventSponsorshipAgreementDocument(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.DO_NOTHING)
    document_name = models.CharField(max_length=5000)
    document_file = models.FileField(upload_to='sponsorship_documents/')
    uploaded_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document for {self.sponsorship.sponsor_name} - {self.uploaded_date}"
    
class EventFeedbackResponse(models.Model):
    feedback = models.ForeignKey(EventFeedback, on_delete=models.DO_NOTHING)
    response_message = models.TextField(max_length=2000)
    response_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Response to {self.feedback.user} - {self.feedback.event.name}"
    
class EventReminder(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    target = models.ManyToManyField(CustomUser, blank=True)
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
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    category = models.ForeignKey(EventCategory, on_delete=models.DO_NOTHING)

    def __str__(self):
        return f"{self.event.name} - {self.category.name}"
    
class EventTagAssignment(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    tag = models.ForeignKey(EventTag, on_delete=models.DO_NOTHING)

    def __str__(self):
        return f"{self.event.name} - {self.tag.name}"

    
# class EventSponsorContactPerson(models.Model):
#     sponsor = models.ForeignKey(EventSponsor, on_delete=models.DO_NOTHING)
#     contact_person_name = models.CharField(max_length=200)
#     contact_person_email = models.EmailField()
#     contact_person_phone = models.CharField(max_length=20)

#     def __str__(self):
#         return f"{self.contact_person_name} - {self.sponsor.sponsor_name}"
    
class EventAttendance(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    user = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)
    check_in_time = models.DateTimeField(auto_now_add=True)
    check_out_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} - {self.event.name}"
    
class EventSponsorBenefit(models.Model):
    sponsor = models.ForeignKey(EventSponsor, on_delete=models.DO_NOTHING)
    benefit_description = models.TextField(max_length=1000)

    def __str__(self):
        return f"Benefit for {self.sponsor.sponsor_name}"
    
class EventSurvey(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    survey_title = models.CharField(max_length=200)
    survey_description = models.TextField(max_length=2000)

    def __str__(self):
        return f"{self.survey_title} - {self.event.name}"
    
class EventSurveyQuestion(models.Model):
    survey = models.ForeignKey(EventSurvey, on_delete=models.DO_NOTHING)
    question_text = models.TextField(max_length=1000)

    def __str__(self):
        return f"Question for {self.survey.survey_title}"
    
class EventSurveyResponse(models.Model):
    question = models.ForeignKey(EventSurveyQuestion, on_delete=models.DO_NOTHING)
    user = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)
    response_text = models.TextField(max_length=2000)

    def __str__(self):
        return f"Response by {self.user} to {self.question.survey.survey_title}"
    
class EventSponsorLogo(models.Model):
    sponsor = models.ForeignKey(EventSponsor, on_delete=models.DO_NOTHING)
    logo = models.ImageField(upload_to='sponsor_logos/')

    def __str__(self):
        return f"Logo for {self.sponsor.sponsor_name}"
    
class EventPromotion(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    promotion_channel = models.CharField(max_length=200)
    promotion_details = models.TextField(max_length=1000)

    def __str__(self):
        return f"Promotion for {self.event.name} via {self.promotion_channel}"
    
class EventMediaCoverage(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    organisation = models.ForeignKey(Organisation, on_delete=models.DO_NOTHING)
    media_outlet = models.CharField(max_length=200)
    coverage_details = models.TextField(max_length=2000)

    def __str__(self):
        return f"Media Coverage for {self.event.name} by {self.media_outlet}"
    
class EventSponsorPayment(models.Model):
    sponsor = models.ForeignKey(EventSponsor, on_delete=models.DO_NOTHING)
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment by {self.sponsor.sponsor_name}"
    
class EventFollowUp(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    user = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)
    follow_up_message = models.TextField(max_length=2000)
    follow_up_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Follow Up for {self.event.name}"
    
class EventCollaboration(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    organisation = models.ForeignKey(Organisation, on_delete=models.DO_NOTHING)
    collaborator_name = models.CharField(max_length=200)
    collaboration_details = models.TextField(max_length=1000)
    entered_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Collaboration with {self.collaborator_name} for {self.event.name}"
    
class EventPartnership(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    organisation = models.ForeignKey(Organisation, on_delete=models.DO_NOTHING)
    partner_name = models.CharField(max_length=200)
    partnership_details = models.TextField(max_length=1000)

    def __str__(self):
        return f"Partnership with {self.partner_name} for {self.event.name}"
    
class EventSponsorshipLevel(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    level_name = models.CharField(max_length=200)
    level_benefits = models.TextField(max_length=1000)
    level_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.level_name} - {self.event.name}"
    
class EventSponsorshipApplication(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)
    organisation = models.ForeignKey(Organisation, on_delete=models.DO_NOTHING)
    user = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)
    applicant_name = models.CharField(max_length=200)
    applicant_contact = models.CharField(max_length=200)
    application_details = models.TextField(max_length=2000)
    application_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Application by {self.applicant_name} for {self.event.name}"
    
class EventSponsorshipApproval(models.Model):
    application = models.ForeignKey(EventSponsorshipApplication, on_delete=models.DO_NOTHING)
    approval_status = models.CharField(max_length=100, choices=APPROVAL_PERM, default='approved')
    approval_reason = models.TextField(max_length=2000)
    approval_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Approval for {self.application.applicant_name} - {self.approval_status}"
    
class EventSponsorshipRejection(models.Model):
    application = models.ForeignKey(EventSponsorshipApplication, on_delete=models.DO_NOTHING)
    rejection_status = models.CharField(max_length=100, choices=APPROVAL_PERM, default='rejected')
    rejection_reason = models.TextField(max_length=2000)
    rejection_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rejection for {self.application.applicant_name} - {self.rejection_reason}"
    
class EventSponsorshipRenewal(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.DO_NOTHING)
    sponsorship_status = models.CharField(max_length=100, choices=APPROVAL_PERM, default='renewed')
    renewal_date = models.DateTimeField(auto_now_add=True)
    renewal_details = models.TextField(max_length=2000)

    def __str__(self):
        return f"Renewal for {self.sponsorship.sponsor_name}"
    
class EventSponsorshipTermination(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.DO_NOTHING)
    sponsorship_status = models.CharField(max_length=100, choices=APPROVAL_PERM, default='inactive')
    termination_date = models.DateTimeField(auto_now_add=True)
    termination_reason = models.TextField(max_length=2000)

    def __str__(self):
        return f"Termination for {self.sponsorship.sponsor_name}"
    
class EventSponsorshipExtension(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.DO_NOTHING)
    sponsorship_status = models.CharField(max_length=100, choices=APPROVAL_PERM, default='extended')
    extension_date = models.DateTimeField(auto_now_add=True)
    extension_details = models.TextField(max_length=2000)

    def __str__(self):
        return f"Extension for {self.sponsorship.sponsor_name}"
    
class EventSponsorshipUpgrade(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.DO_NOTHING)
    sponsorship_status = models.CharField(max_length=100, choices=APPROVAL_PERM, default='upgraded')
    upgrade_date = models.DateTimeField(auto_now_add=True)
    upgrade_details = models.TextField(max_length=2000)

    def __str__(self):
        return f"Upgrade for {self.sponsorship.sponsor_name}"
    
class EventSponsorshipDowngrade(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.DO_NOTHING)
    sponsorship_status = models.CharField(max_length=100, choices=APPROVAL_PERM, default='downgraded')
    downgrade_date = models.DateTimeField(auto_now_add=True)
    downgrade_details = models.TextField(max_length=2000)

    def __str__(self):
        return f"Downgrade for {self.sponsorship.sponsor_name}"
    
class EventSponsorshipTransfer(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.DO_NOTHING)
    sponsorship_status = models.CharField(max_length=100, choices=APPROVAL_PERM, default='transferred')
    transfer_date = models.DateTimeField(auto_now_add=True)
    new_sponsor_name = models.CharField(max_length=200)

    def __str__(self):
        return f"Transfer of {self.sponsorship.sponsor_name} to {self.new_sponsor_name}"
    
class EventSponsorshipReport(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.DO_NOTHING)
    report_date = models.DateTimeField(auto_now_add=True)
    report_details = models.TextField(max_length=2000)

    def __str__(self):
        return f"Report for {self.sponsorship.sponsor_name} - {self.report_date}"

class EventSponsorshipHistory(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.DO_NOTHING)
    report = models.ForeignKey(EventSponsorshipReport, on_delete=models.DO_NOTHING)
    change_date = models.DateTimeField(auto_now_add=True)
    change_details = models.TextField(max_length=2000)

    def __str__(self):
        return f"History for {self.sponsorship.sponsor_name} - {self.change_date}"
    
class EventSponsorshipFeedback(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.DO_NOTHING)
    user = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)
    feedback_message = models.TextField(max_length=2000)
    feedback_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for {self.sponsorship.sponsor_name} - {self.feedback_date}"
    
class EventSponsorshipEvaluation(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.DO_NOTHING)
    evaluation_date = models.DateTimeField(auto_now_add=True)
    evaluation_details = models.TextField(max_length=2000)
    evaluated_by = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)

    def __str__(self):
        return f"Evaluation for {self.sponsorship.sponsor_name} - {self.evaluation_date}"
    
class EventSponsorshipRecognition(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.DO_NOTHING)
    recognition_date = models.DateTimeField(auto_now_add=True)
    recognition_details = models.TextField(max_length=2000)

    def __str__(self):
        return f"Recognition for {self.sponsorship.sponsor_name} - {self.recognition_date}"
    
class EventSponsorshipCertificate(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.DO_NOTHING)
    certificate_file = models.FileField(upload_to='sponsorship_certificates/')
    issued_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Certificate for {self.sponsorship.sponsor_name} - {self.issued_date}"
    
class EventSponsorshipInvoice(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.DO_NOTHING)
    invoice_file = models.FileField(upload_to='sponsorship_invoices/')
    issued_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invoice for {self.sponsorship.sponsor_name} - {self.issued_date}"
    
class EventSponsorshipContract(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.DO_NOTHING)
    contract_file = models.FileField(upload_to='sponsorship_contracts/')
    signed_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Contract for {self.sponsorship.sponsor_name} - {self.signed_date}"
    
class EventSponsorshipLetter(models.Model):
    sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.DO_NOTHING)
    letter_file = models.FileField(upload_to='sponsorship_letters/')
    issued_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Letter for {self.sponsorship.sponsor_name} - {self.issued_date}"
    
# class EventSponsorshipContactInfo(models.Model):
#     sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.DO_NOTHING)
#     contact_name = models.CharField(max_length=200)
#     contact_email = models.EmailField()
#     contact_phone = models.CharField(max_length=20)

#     def __str__(self):
#         return f"Contact for {self.sponsorship.sponsor_name} - {self.contact_name}"
# class EventSponsorshipCoordinator(models.Model):
#     sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.DO_NOTHING)
#     coordinator_name = models.CharField(max_length=200)
#     coordinator_email = models.EmailField()
#     coordinator_phone = models.CharField(max_length=20)

#     def __str__(self):
#         return f"Coordinator for {self.sponsorship.sponsor_name} - {self.coordinator_name}"
# class EventSponsorshipManager(models.Model):
#     sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.DO_NOTHING)
#     manager_name = models.CharField(max_length=200)
#     manager_email = models.EmailField()
#     manager_phone = models.CharField(max_length=20)

#     def __str__(self):
#         return f"Manager for {self.sponsorship.sponsor_name} - {self.manager_name}"
# class EventSponsorshipDirector(models.Model):
#     sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.DO_NOTHING)
#     director_name = models.CharField(max_length=200)
#     director_email = models.EmailField()
#     director_phone = models.CharField(max_length=20)

#     def __str__(self):
#         return f"Director for {self.sponsorship.sponsor_name} - {self.director_name}"
# class EventSponsorshipExecutive(models.Model):
#     sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.DO_NOTHING)
#     executive_name = models.CharField(max_length=200)
#     executive_email = models.EmailField()
#     executive_phone = models.CharField(max_length=20)

#     def __str__(self):
#         return f"Executive for {self.sponsorship.sponsor_name} - {self.executive_name}"
# class EventSponsorshipTeamMember(models.Model):
#     sponsorship = models.ForeignKey(EventSponsorAgreement, on_delete=models.DO_NOTHING)
#     team_member_name = models.CharField(max_length=200)
#     team_member_email = models.EmailField()
#     team_member_phone = models.CharField(max_length=20)

#     def __str__(self):
#         return f"Team Member for {self.sponsorship.sponsor_name} - {self.team_member_name}"
# class EventSponsorshipContactPersonRole(models.Model):
#     contact_person = models.ForeignKey(EventSponsorshipContactInfo, on_delete=models.DO_NOTHING)
#     role_name = models.CharField(max_length=200)
#     role_description = models.TextField(max_length=1000)

#     def __str__(self):#         return f"Role {self.role_name} for {self.contact_person.contact_name}"


# Import enhanced models to register them with Django
from .enhanced_models import *

