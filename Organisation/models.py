from django.db import models
from datetime import datetime

# Create your models here.
ORG_TYPES = (
    ('business', 'Business Enterprise'),
    ('ngo', 'Non-Governmental Organisation (NGO)'),
    ('learning_inst', 'Learning Institution'),
    ('go', 'Governmental Organisation'),
    ('ministry', 'Ministry Organisation'),
    ('restaurant', 'Restaurant'),
    ('hotel', 'Hotel'),
    ('coffee_shop', 'Coffee Shop'),
    ('supermarket', 'Supermarket'),
    ('store', 'Store'),
    ('service_provider', 'Service Provider'),
    ('food_shop', 'Food Shop'),
    ('other', 'Other')
)

class Organisation(models.Model):
    name = models.CharField(max_length=1000)
    origin = models.CharField(max_length=500, blank=True, default='')
    abbreviation = models.CharField(max_length=200, blank=True, default='')
    address = models.CharField(max_length=200, blank=True, default='')
    postal_code = models.CharField(max_length=200, blank=True, default='')
    town = models.CharField(max_length=100, blank=True, default='')
    city = models.CharField(max_length=500, blank=True, default='')
    org_type = models.CharField(max_length=200, choices=ORG_TYPES, default='business')
    is_learning_inst = models.BooleanField(default=False)
    industry = models.CharField(max_length=5000, blank=True, default='')
    created_on = models.DateTimeField(default=datetime.now)
    members = models.ManyToManyField('Authentication.CustomUser', blank=True)
    
    # Creator tracking
    # Creator tracking
    created_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_organisations')

    # Media
    profile_picture = models.ImageField(upload_to='organisation_profiles/', null=True, blank=True)
    cover_picture = models.ImageField(upload_to='organisation_covers/', null=True, blank=True)



class OrgBranch(models.Model):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=200)
    branch_code = models.CharField(max_length=200, unique=True, primary_key=True)
    origin = models.CharField(max_length=500, blank=True)
    region = models.CharField(max_length=500, blank=True)
    abbreviation = models.CharField(max_length=200, blank=True)
    address = models.CharField(max_length=200, blank=True)
    postal_code = models.CharField(max_length=200, blank=True)
    town = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=500, blank=True)
    created_on = models.DateTimeField(default=datetime.now)
    # members field removed as it is now handled by OrganisationMember or can remain as shortcut?
    # Better to remove ManyToMany here if we use OrganisationMember. But converting ManyToMany to intermediate model is a heavy migration.
    # The user asked for "add members with titles".
    # I will keep 'members' field if needed for backward compatibility or remove it?
    # The existing code has `members = models.ManyToManyField(...)`. I should probably deprecate it or replace it.
    # Given the refactor, I'll remove it from the definition here and rely on OrganisationMember, OR keep it but it's redundant.
    # Let's start by modifying the relationship fields. keeping members for now to reduce friction, but will add OrganisationMember.
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
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='divisions', null=True)
    org_branch = models.ForeignKey(OrgBranch, on_delete=models.CASCADE, related_name='divisions', null=True)
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
    division = models.ForeignKey(Division, on_delete=models.CASCADE, related_name='departments', null=True)
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
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='sections', null=True)
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
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='units', null=True)
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
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='teams', null=True)
    name = models.CharField(max_length=500)
    team_code = models.CharField(max_length=200, unique=True, primary_key=True)
    created_on = models.DateTimeField(default=datetime.now)
    members = models.ManyToManyField('Authentication.CustomUser', blank=True)


class Committee(models.Model):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='committees', null=True)
    name = models.CharField(max_length=500)
    committee_code = models.CharField(max_length=200, unique=True, primary_key=True)
    created_on = models.DateTimeField(default=datetime.now)
    members = models.ManyToManyField('Authentication.CustomUser', blank=True)


class Board(models.Model):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='boards', null=True)
    name = models.CharField(max_length=500)
    board_code = models.CharField(max_length=200, unique=True, primary_key=True)
    created_on = models.DateTimeField(default=datetime.now)
    members = models.ManyToManyField('Authentication.CustomUser', blank=True)


class Project(models.Model):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='projects', null=True)
    name = models.CharField(max_length=500)
    project_code = models.CharField(max_length=200, unique=True, primary_key=True)
    created_on = models.DateTimeField(default=datetime.now)
    members = models.ManyToManyField('Authentication.CustomUser', blank=True)


class Program(models.Model):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='programs', null=True)
    name = models.CharField(max_length=500)
    program_code = models.CharField(max_length=200, unique=True, primary_key=True)
    created_on = models.DateTimeField(default=datetime.now)
    members = models.ManyToManyField('Authentication.CustomUser', blank=True)


class Centre(models.Model):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='centres', null=True)
    name = models.CharField(max_length=500)
    centre_code = models.CharField(max_length=200, unique=True, primary_key=True)
    created_on = models.DateTimeField(default=datetime.now)
    members = models.ManyToManyField('Authentication.CustomUser', blank=True)


class Institute(models.Model):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='institutes', null=True)
    name = models.CharField(max_length=500)
    institute_code = models.CharField(max_length=200, unique=True, primary_key=True)
    created_on = models.DateTimeField(default=datetime.now)
    members = models.ManyToManyField('Authentication.CustomUser', blank=True)

class OtherOrgUnit(models.Model):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='other_units', null=True)
    parent_units = models.ManyToManyField('self', blank=True)
    name = models.CharField(max_length=500)
    unit_code = models.CharField(max_length=200, unique=True, primary_key=True)
    created_on = models.DateTimeField(default=datetime.now)
    members = models.ManyToManyField('Authentication.CustomUser', blank=True)


# New Organisation Member Model
class OrganisationMember(models.Model):
    """
    Member of an organisation with role and title.
    Allows managing users within the organisation similarly to InstitutionMember.
    """
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='organisation_members')
    user = models.ForeignKey('Authentication.CustomUser', on_delete=models.CASCADE, related_name='org_memberships')
    
    role = models.CharField(max_length=50, choices=(
        ('admin', 'Administrator'),
        ('moderator', 'Moderator'),
        ('member', 'Member'),
    ), default='member')
    
    title = models.CharField(max_length=200, blank=True, help_text="Custom editable title (e.g. 'Head of Marketing')")
    
    joined_at = models.DateTimeField(default=datetime.now)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('organisation', 'user')
        verbose_name = 'Organisation Member'
        verbose_name_plural = 'Organisation Members'
        
    def __str__(self):
        return f"{self.user.email} - {self.title or self.role} at {self.organisation.name}"



