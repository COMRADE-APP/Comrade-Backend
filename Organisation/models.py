from django.db import models
from datetime import datetime

# Create your models here.
ORG_TYPES = (
    ('business', 'Business Enterprise'),
    ('ngo', 'Non-Governmental Organisation (NGO)'),
    ('learning_inst', 'Learning Institution'),
    ('go', 'Governmental Organisation'),
    ('ministry', 'Ministry Organisation'),
    ('other', 'Other')
)

class Organisation(models.Model):
    name = models.CharField(max_length=1000)
    origin = models.CharField(max_length=500)
    abbreviation = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    postal_code = models.CharField(max_length=200)
    town = models.CharField(max_length=100)
    city = models.CharField(max_length=500)
    org_type = models.CharField(max_length=200, choices=ORG_TYPES, default='business')
    is_learning_inst = models.BooleanField(default=False)
    industry = models.CharField(max_length=5000)
    created_on = models.DateTimeField(default=datetime.now)
    members = models.ManyToManyField('Authentication.CustomUser', blank=True)
    
    # Creator tracking
    created_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_organisations')



class OrgBranch(models.Model):
    organisation = models.OneToOneField(Organisation, on_delete=models.DO_NOTHING)
    name = models.CharField(max_length=200)
    branch_code = models.CharField(max_length=200, unique=True, primary_key=True)
    origin = models.CharField(max_length=500)
    region = models.CharField(max_length=500)
    abbreviation = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    postal_code = models.CharField(max_length=200)
    town = models.CharField(max_length=100)
    city = models.CharField(max_length=500)
    created_on = models.DateTimeField(default=datetime.now)
    members = models.ManyToManyField('Authentication.CustomUser', blank=True)




# Organization
# ├── Divisions
# │   └── Departments
# │       └── Units/Sections
# │           └── Teams
# ├── Committees / Boards
# ├── Offices / Branches
# ├── Programs / Projects
# └── Centers / Institutes
class Division(models.Model):
    organistion = models.OneToOneField(Organisation, on_delete=models.DO_NOTHING, null=True)
    org_branch = models.OneToOneField(OrgBranch, on_delete=models.DO_NOTHING, null=True)
    name = models.CharField(max_length=500)
    div_code = models.CharField(max_length=200, unique=True, primary_key=True)
    created_on = models.DateTimeField(default=datetime.now)
    members = models.ManyToManyField('Authentication.CustomUser', blank=True)
    
    # Approval workflow fields
    approval_status = models.CharField(max_length=20, choices=(
        ('approved', 'Approved'),
        ('pending', 'Pending Approval'),
        ('rejected', 'Rejected'),
    ), default='approved')
    created_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_org_divisions')
    approved_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_org_divisions')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    
class Department(models.Model):
    division = models.OneToOneField(Division, on_delete=models.DO_NOTHING, null=True)
    name = models.CharField(max_length=500)
    dep_code = models.CharField(max_length=200, unique=True, primary_key=True)
    created_on = models.DateTimeField(default=datetime.now)
    members = models.ManyToManyField('Authentication.CustomUser', blank=True)
    
    # Approval workflow fields
    approval_status = models.CharField(max_length=20, choices=(
        ('approved', 'Approved'),
        ('pending', 'Pending Approval'),
        ('rejected', 'Rejected'),
    ), default='approved')
    created_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_org_departments')
    approved_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_org_departments')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)


class Section(models.Model):
    department = models.OneToOneField(Department, on_delete=models.DO_NOTHING, null=True)
    name = models.CharField(max_length=500)
    section_code = models.CharField(max_length=200, unique=True, primary_key=True)
    created_on = models.DateTimeField(default=datetime.now)
    members = models.ManyToManyField('Authentication.CustomUser', blank=True)
    
    # Approval workflow fields
    approval_status = models.CharField(max_length=20, choices=(
        ('approved', 'Approved'),
        ('pending', 'Pending Approval'),
        ('rejected', 'Rejected'),
    ), default='approved')
    created_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_org_sections')
    approved_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_org_sections')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)


class Unit(models.Model):
    department = models.OneToOneField(Department, on_delete=models.DO_NOTHING, null=True)
    name = models.CharField(max_length=500)
    unit_code = models.CharField(max_length=200, unique=True, primary_key=True)
    created_on = models.DateTimeField(default=datetime.now)
    members = models.ManyToManyField('Authentication.CustomUser', blank=True)
    
    # Approval workflow fields
    approval_status = models.CharField(max_length=20, choices=(
        ('approved', 'Approved'),
        ('pending', 'Pending Approval'),
        ('rejected', 'Rejected'),
    ), default='approved')
    created_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_org_units')
    approved_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_org_units')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)


class Team(models.Model):
    section = models.OneToOneField(Section, on_delete=models.DO_NOTHING, null=True)
    name = models.CharField(max_length=500)
    team_code = models.CharField(max_length=200, unique=True, primary_key=True)
    created_on = models.DateTimeField(default=datetime.now)
    members = models.ManyToManyField('Authentication.CustomUser', blank=True)


class Committee(models.Model):
    organistaion = models.OneToOneField(Organisation, on_delete=models.DO_NOTHING, null=True)
    name = models.CharField(max_length=500)
    committee_code = models.CharField(max_length=200, unique=True, primary_key=True)
    created_on = models.DateTimeField(default=datetime.now)
    members = models.ManyToManyField('Authentication.CustomUser', blank=True)


class Board(models.Model):
    organistaion = models.OneToOneField(Organisation, on_delete=models.DO_NOTHING, null=True)
    name = models.CharField(max_length=500)
    board_code = models.CharField(max_length=200, unique=True, primary_key=True)
    created_on = models.DateTimeField(default=datetime.now)
    members = models.ManyToManyField('Authentication.CustomUser', blank=True)


class Project(models.Model):
    organistaion = models.OneToOneField(Organisation, on_delete=models.DO_NOTHING, null=True)
    name = models.CharField(max_length=500)
    project_code = models.CharField(max_length=200, unique=True, primary_key=True)
    created_on = models.DateTimeField(default=datetime.now)
    members = models.ManyToManyField('Authentication.CustomUser', blank=True)


class Program(models.Model):
    organistaion = models.OneToOneField(Organisation, on_delete=models.DO_NOTHING, null=True)
    name = models.CharField(max_length=500)
    program_code = models.CharField(max_length=200, unique=True, primary_key=True)
    created_on = models.DateTimeField(default=datetime.now)
    members = models.ManyToManyField('Authentication.CustomUser', blank=True)


class Centre(models.Model):
    organistaion = models.OneToOneField(Organisation, on_delete=models.DO_NOTHING, null=True)
    name = models.CharField(max_length=500)
    centre_code = models.CharField(max_length=200, unique=True, primary_key=True)
    created_on = models.DateTimeField(default=datetime.now)
    members = models.ManyToManyField('Authentication.CustomUser', blank=True)


class Institute(models.Model):
    organistaion = models.OneToOneField(Organisation, on_delete=models.DO_NOTHING, null=True)
    name = models.CharField(max_length=500)
    institute_code = models.CharField(max_length=200, unique=True, primary_key=True)
    created_on = models.DateTimeField(default=datetime.now)
    members = models.ManyToManyField('Authentication.CustomUser', blank=True)

class OtherOrgUnit(models.Model):
    organisation = models.OneToOneField(Organisation, on_delete=models.DO_NOTHING, null=True)
    parent_units = models.ManyToManyField('self', blank=True)
    name = models.CharField(max_length=500)
    unit_code = models.CharField(max_length=200, unique=True, primary_key=True)
    created_on = models.DateTimeField(default=datetime.now)
    members = models.ManyToManyField('Authentication.CustomUser', blank=True)



