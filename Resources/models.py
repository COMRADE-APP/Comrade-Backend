from django.db import models
from rest_framework.exceptions import ValidationError
from Rooms.models import Room, DefaultRoom, DirectMessageRoom
from Authentication.models import CustomUser as Cus
from Institution.models import Institution, InstBranch, Faculty, VCOffice, InstDepartment, AdminDep, Programme, HR, Admissions, HealthServices, Security, StudentAffairs, SupportServices, Finance, Marketing, Legal, ICT, CareerOffice, Counselling, RegistrarOffice, Transport, Library, Hostel, Cafeteria, OtherInstitutionUnit
from Organisation.models import Organisation, OrgBranch, Division, Department, Section, Team, Project, Centre, Committee, Board, Unit, Institute, Program, OtherOrgUnit
from datetime import datetime



# Resource types
RESOURCE_TYPES = (
    ('media_link', 'Media Link'),
    ('text', 'Text'),
    ('image', 'Image file'),
    ('doc', 'Document File'),
)
VIS_TYPES = (
    ('public', 'Public'),
    ('private', 'Private'),
    ('only_me', 'Only Me'),
    ('course', 'Your Course or Class'),
    ('faculty', 'Your Faculty or School'),
    ('institutional', 'Your Institution'),
    ('organisational', 'Your Organisation'),
    ('group', 'Your Group or Section')
)


class Resource(models.Model):
    visibility = models.CharField(max_length=20, choices=VIS_TYPES, default='public')
    title = models.CharField(max_length=100, default='', )
    desc = models.TextField(max_length=1000, default='')
    file_type = models.CharField(max_length=20, choices=RESOURCE_TYPES, default='doc')
    res_file = models.FileField(upload_to="uploads/", blank=True, null=True)
    res_text = models.TextField(max_length=50000, blank=True, null=True)
    created_by = models.ForeignKey(Cus, related_name='created_resources', on_delete=models.CASCADE, null=True)
    authors = models.ManyToManyField(Cus, related_name='authored_resources', blank=True)
    editors = models.ManyToManyField(Cus, related_name='edited_resources', blank=True)
    created_on = models.DateTimeField(default=datetime.now())
    

    def clean(self):
        """Custom validation to ensure correct field usage."""
        if self.file_type == "text" and not self.res_text:
            raise ValidationError("Text resource requires res_text content.")
        if self.file_type in ["image", "doc"] and not self.res_file:
            raise ValidationError("File upload is required for this type.")
        if self.file_type == "media_link" and not isinstance(self.res_file, str):
            raise ValidationError("Media Link should be a valid URL.")

    def save(self, *args, **kwargs):
        """Override save method to ensure correct field is used."""
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class VisibilityLog(models.Model):
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    changed_by = models.ForeignKey(Cus, on_delete=models.CASCADE, null=True)
    old_visibility = models.CharField(max_length=20, choices=VIS_TYPES)
    new_visibility = models.CharField(max_length=20, choices=VIS_TYPES)
    changed_at = models.DateTimeField(auto_now=True)
    
class ResourceVisibility(models.Model):
    resource = models.OneToOneField(Resource, on_delete=models.DO_NOTHING)
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

    def __str__(self):
        return f"Visibility settings for {self.resource.title}"
    

    

