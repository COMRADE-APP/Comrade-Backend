from django.db import models
from rest_framework.exceptions import ValidationError
from Rooms.models import Room, DefaultRoom, DirectMessageRoom
from Authentication.models import Profile
from Institution.models import Institution, InstBranch, Faculty, VCOffice, InstDepartment, AdminDep, Programme, HR, Admissions, HealthServices, Security, StudentAffairs, SupportServices, Finance, Marketing, Legal, ICT, CareerOffice, Counselling, RegistrarOffice, Transport, Library, Hostel, Cafeteria, OtherInstitutionUnit
from Organisation.models import Organisation, OrgBranch, Division, Department, Section, Team, Project, Centre, Committee, Board, Unit, Institute, Program, OtherOrgUnit
from datetime import datetime
from Events.models import Event 
import uuid



# Resource types
RESOURCE_TYPES = (
    ('media_link', 'Media Link'),
    ('text', 'Text'),
    ('image', 'Image file'),
    ('doc', 'Document File'),
)

# Operation Status for models (used together with visibility model)
OPERATION_STATUS = (
    ('active', 'Active'),
    ('deactivated', 'Deactivated'),
    ('deleted', 'Deleted'),
    ('suspended', 'Suspended'),
    ('under_review', 'Under Review'),
    ('draft', 'Draft'),
    ('pending', 'Pending'),
    ('sensored', 'Sensored'),
    ('blocked', 'Blocked'),
)

# Visibility types
VIS_TYPES = (
    ('only_me', 'Only Me'),
    ('rooms', 'Rooms'),
    ('default_rooms', 'Default Rooms'),
    ('direct_message_rooms', 'Direct Message Rooms'),
    ('organisations', 'Organisations'),
    ('organisation_branches', 'Organisation Branches'),
    ('departments', 'Departments'),
    ('sections', 'Sections'),
    ('committees', 'Committees'),
    ('units', 'Units'),
    ('programs', 'Programs'),
    ('projects', 'Projects'),
    ('centres', 'Centres'),
    ('teams', 'Teams'),
    ('divisions', 'Divisions'),
    ('boards', 'Boards'),
    ('institutes', 'Institutes'),
    ('other_organisation_units', 'Other Organisation Units'),
    ('institutions', 'Institutions'),
    ('institution_branches', 'Institution Branches'),
    ('faculties', 'Faculties'),
    ('vc_offices', 'VC Offices'),
    ('inst_departments', 'Institution Departments'),
    ('admin_deps', 'Admin Departments'),
    ('programmes', 'Programmes'),
    ('hrs', 'HRs'),
    ('admissions', 'Admissions'),
    ('health_services', 'Health Services'),
    ('securities', 'Securities'),
    ('student_affairs', 'Student Affairs'),
    ('support_services', 'Support Services'),
    ('finances', 'Finances'),
    ('marketings', 'Marketings'),
    ('legals', 'Legals'),
    ('icts', 'ICTs'),
    ('career_offices', 'Career Offices'),
    ('counsellings', 'Counsellings'),
    ('registrar_offices', 'Registrar Offices'),
    ('transports', 'Transports'),
    ('libraries', 'Libraries'),
    ('hostels', 'Hostels'),
    ('cafeterias', 'Cafeterias'),
    ('other_institution_units', 'Other Institution Units'),
    ('public', 'Public'),
)

# Visibility main entity options
VIS_OPT_TYPES = (
    ('comrade', 'Comrade'),
    ('creator', 'Creator'),
    ('admins', 'Entity Admins'),
    ('admins_moderators', 'Admins and Moderators'),
    ('resources', 'Resources'),
    ('rooms', 'Rooms'),
    ('default_rooms', 'Default Rooms'),
    ('direct_message_rooms', 'Direct Message Rooms'),
    ('organisations', 'Organisations'),
    ('organisation_branches', 'Organisation Branches'),
    ('departments', 'Departments'),
    ('sections', 'Sections'),
    ('committees', 'Committees'),
    ('units', 'Units'),
    ('programs', 'Programs'),
    ('projects', 'Projects'),
    ('centres', 'Centres'),
    ('teams', 'Teams'),
    ('divisions', 'Divisions'),
    ('boards', 'Boards'),
    ('institutes', 'Institutes'),
    ('other_organisation_units', 'Other Organisation Units'),
    ('institutions', 'Institutions'),
    ('institution_branches', 'Institution Branches'),
    ('faculties', 'Faculties'),
    ('vc_offices', 'VC Offices'),
    ('inst_departments', 'Institution Departments'),
    ('admin_deps', 'Admin Departments'),
    ('programmes', 'Programmes'),
    ('hrs', 'HRs'),
    ('admissions', 'Admissions'),
    ('health_services', 'Health Services'),
    ('securities', 'Securities'),
    ('student_affairs', 'Student Affairs'),
    ('support_services', 'Support Services'),
    ('finances', 'Finances'),
    ('marketings', 'Marketings'),
    ('legals', 'Legals'),
    ('icts', 'ICTs'),
    ('career_offices', 'Career Offices'),
    ('counsellings', 'Counsellings'),
    ('registrar_offices', 'Registrar Offices'),
    ('transports', 'Transports'),
    ('libraries', 'Libraries'),
    ('hostels', 'Hostels'),
    ('cafeterias', 'Cafeterias'),
    ('other_institution_units', 'Other Institution Units'),
    ('public', 'Public'),
)



class Resource(models.Model):
    visibility = models.CharField(max_length=200, choices=VIS_TYPES, default='public')
    title = models.CharField(max_length=100, default='', )
    desc = models.TextField(max_length=1000, default='')
    file_type = models.CharField(max_length=20, choices=RESOURCE_TYPES, default='doc')
    res_file = models.FileField(upload_to='resources/docs', blank=True, null=True)
    res_text = models.TextField(blank=True, null=True)
    res_link = models.URLField(blank=True, null=True)
    created_by = models.ForeignKey(Profile, related_name='created_resources', on_delete=models.CASCADE, null=True)
    price_tag = models.DecimalField(decimal_places=2, max_digits=100, default=0.0)
    authors = models.ManyToManyField(Profile, related_name='authored_resources', blank=True)
    editors = models.ManyToManyField(Profile, related_name='edited_resources', blank=True)
    created_on = models.DateTimeField(default=datetime.now)
    

    def clean(self):
        # Ensure content matches file_type
        if self.file_type == 'text' and not self.res_text:
            raise ValidationError({'res_text': 'Text resource requires res_text content.'})


        if self.file_type == 'image' and not self.res_file:
            raise ValidationError({'res_file': 'Image resource requires an uploaded file.'})


        if self.file_type == 'doc' and not self.res_file:
            raise ValidationError({'res_file': 'Document resource requires an uploaded file.'})


        if self.file_type == 'media_link' and not self.res_link:
            raise ValidationError({'res_link': 'Media link resource requires a URL in res_link.'})

    def save(self, *args, **kwargs):
        """Override save method to ensure correct field is used."""
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


    
class ResourceVisibility(models.Model):
    resource = models.OneToOneField(Resource, on_delete=models.CASCADE, related_name='resource_visibility')
    scheduled_time = models.DateTimeField(null=True, blank=True)
    expiry_time = models.DateTimeField(null=True, blank=True)
    rooms = models.ManyToManyField(Room, blank=True)
    default_rooms = models.ManyToManyField(DefaultRoom, blank=True)
    direct_message_rooms = models.ManyToManyField(DirectMessageRoom, blank=True)
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
    events = models.ManyToManyField(Event, blank=True)

    def __str__(self):
        return f"Visibility settings for {self.resource.title}"
    

class VisibilityLog(models.Model):
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='visibility_logs')
    changed_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, related_name='visibility_changed_logs', null=True)
    previous_visibility = models.ForeignKey(ResourceVisibility, on_delete=models.SET_NULL, related_name='previous_visibility_logs', null=True)
    new_visibility = models.ForeignKey(ResourceVisibility, on_delete=models.SET_NULL, related_name='new_visibility_logs', null=True)
    changed_on = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return f"Visibility change for {self.resource.title} by {self.changed_by.username} on {self.changed_on}"
    

class Link(models.Model):
    url = models.URLField(max_length=5000)
    description = models.TextField(max_length=500, null=True, blank=True)
    created_by = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='created_links')
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.url
    

# Visibility for overall models
class Visibility(models.Model):
    main_entity = models.CharField(max_length=1000, choices=VIS_OPT_TYPES, default='resource')
    visibility_code = models.CharField(max_length=2000, unique=True, primary_key=True)
    operation_state = models.CharField(choices=OPERATION_STATUS, default='pending')
    scheduled_time = models.DateTimeField(blank=True)
    expiry_time = models.DateTimeField(blank=True)
    resources = models.ManyToManyField(Resource, blank=True, related_name='main_visibility_resources')
    rooms = models.ManyToManyField(Room, blank=True)
    default_rooms = models.ManyToManyField(DefaultRoom, blank=True)
    direct_message_rooms = models.ManyToManyField(DirectMessageRoom, blank=True)
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
    events = models.ManyToManyField(Event, blank=True)

    def save(self, *args, **kwargs):
        if not self.visibility_code:
            self.visibility_code = self.generate_invitation_code()
        super().save(*args, **kwargs)
    
    def generate_invitation_code(self):
        return f'{uuid.uuid4().hex[:10].upper()}-->{datetime.now.day}'

    def __str__(self):
        return f"Visibility settings for {self.resource.title}"
    

class MainVisibilityLog(models.Model):
    changed_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, related_name='main_visibility_changed_logs', null=True)
    previous_visibility = models.ForeignKey(ResourceVisibility, on_delete=models.SET_NULL, related_name='previous_main_visibility_logs', null=True)
    new_visibility = models.ForeignKey(ResourceVisibility, on_delete=models.SET_NULL, related_name='new_main_visibility_logs', null=True)
    changed_on = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return f"Visibility change for {self.resource.title} by {self.changed_by.username} on {self.changed_on}"

