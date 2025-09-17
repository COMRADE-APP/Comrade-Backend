from django.db import models
from django.contrib.auth.models import User, AbstractUser
from django.contrib.auth.admin import UserAdmin
from Institution.models import Institution, InstBranch
from Organisation.models import Organisation, OrgBranch

import datetime

USER_TYPE = (
    ('admin', 'Administrator (Comrade)'),
    ('staff', 'Staff'),
    ('lecturer', 'Lecturer'),
    ('student', 'Student'),
    ('student_admin', 'Student Admin'),
    ('institutional_admin', 'Institutional Admin'),
    ('institutional_staff', 'Institutional Staff'),
    ('organisational_admin', 'Organisational Admin'),
    ('organisational_staff', 'Organisational Staff'),
)
class CustomUser(AbstractUser):
    username = None # removes user name
    first_name = models.CharField(max_length=200)
    middle_name = models.CharField(max_length=200, null=True, default='N/A')
    last_name = models.CharField(max_length=200)
    user_type = models.CharField(max_length=200, choices=USER_TYPE, default='student')
    email = models.EmailField(unique=True)

    USERNAME_FIELD = [email]

class Student(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    admission_number = models.CharField(max_length=100, unique=True, primary_key=True)
    year_of_admission = models.IntegerField(default=1)
    year_of_study = models.IntegerField(default=1)
    current_semester = models.IntegerField(default=1)
    faculty = models.CharField(max_length=200)
    course = models.CharField(max_length=200)
    institution = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=15)
    password = models.CharField(max_length=200)

    def __str__(self):
        return self.user.first_name + " " + self.user.last_name
    
class StudentAdmin(models.Model):
    user = models.OneToOneField(Student, on_delete=models.DO_NOTHING)

class Lecturer(UserAdmin):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

class OrgStaff(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    staff_id = models.CharField(max_length=200, unique=True, primary_key=True)
    staff_role = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    current_organisation = models.OneToOneField(Organisation, on_delete=models.DO_NOTHING, null=True)
    current_org_branch = models.OneToOneField(OrgBranch, on_delete=models.DO_NOTHING, null=True)
    previous_organisations = models.ManyToManyField(Organisation, null=True)
    previous_org_branch = models.ManyToManyField(OrgBranch, null=True)
    dob = models.DateField(auto_now=True)
    nationality = models.CharField(max_length=300)
    country_of_residence = models.CharField(max_length=300)
    current_institution = models.OneToOneField(Institution, on_delete=models.DO_NOTHING, null=True)
    current_inst_branch = models.OneToOneField(InstBranch, on_delete=models.DO_NOTHING, null=True)
    previous_institutions = models.ManyToManyField(Institution, null=True)
    previous_inst_branch = models.ManyToManyField(InstBranch, null=True)
    interests = models.CharField(max_length=5000) # TODO: remember to change this into a model reference of Interest
    created_at = models.DateTimeField(auto_now=True)

class OrgAdmin(models.Model):
    user = models.OneToOneField(OrgStaff, on_delete=models.DO_NOTHING)

