from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from Institution.models import Institution, InstBranch
from Organisation.models import Organisation, OrgBranch

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

from django.contrib.auth.models import BaseUserManager

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    username = None
    first_name = models.CharField(max_length=200)
    middle_name = models.CharField(max_length=200, null=True, default='N/A')
    last_name = models.CharField(max_length=200)
    user_type = models.CharField(max_length=200, choices=USER_TYPE, default='student')
    email = models.EmailField(unique=True)

    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = CustomUserManager()


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
        return f"{self.user.first_name} {self.user.last_name}"


class StudentAdmin(models.Model):
    user = models.OneToOneField(Student, on_delete=models.DO_NOTHING)


class Lecturer(models.Model):   # FIXED
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)


class OrgStaff(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    staff_id = models.CharField(max_length=200, unique=True, primary_key=True)
    staff_role = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)

    current_organisation = models.OneToOneField(
        Organisation, on_delete=models.DO_NOTHING, null=True,
        related_name="current_staff"
    )
    current_org_branch = models.OneToOneField(
        OrgBranch, on_delete=models.DO_NOTHING, null=True,
        related_name="current_branch_staff"
    )
    previous_organisations = models.ManyToManyField(
        Organisation, related_name="previous_staff"
    )
    previous_org_branch = models.ManyToManyField(
        OrgBranch, related_name="previous_branch_staff"
    )

    dob = models.DateField(auto_now=False)
    nationality = models.CharField(max_length=300)
    country_of_residence = models.CharField(max_length=300)

    current_institution = models.OneToOneField(
        Institution, on_delete=models.DO_NOTHING, null=True,
        related_name="current_inst_staff"
    )
    current_inst_branch = models.OneToOneField(
        InstBranch, on_delete=models.DO_NOTHING, null=True,
        related_name="current_inst_branch_staff"
    )
    previous_institutions = models.ManyToManyField(
        Institution, related_name="previous_inst_staff"
    )
    previous_inst_branch = models.ManyToManyField(
        InstBranch, related_name="previous_inst_branch_staff"
    )

    interests = models.CharField(max_length=5000)
    created_at = models.DateTimeField(auto_now=True)


class OrgAdmin(models.Model):
    user = models.OneToOneField(OrgStaff, on_delete=models.DO_NOTHING)


class InstStaff(models.Model):
    user = models.OneToOneField(StudentAdmin, on_delete=models.DO_NOTHING)
    institution = models.OneToOneField(Institution, on_delete=models.DO_NOTHING)
    inst_branch = models.OneToOneField(InstBranch, on_delete=models.DO_NOTHING)
    staff_id = models.CharField(max_length=200, unique=True, primary_key=True)
    staff_role = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    previous_institutions = models.ManyToManyField(
        Institution, related_name="previous_inst_admins")
    previous_inst_branch = models.ManyToManyField(
        InstBranch, related_name="previous_inst_branch_admins")
    dob = models.DateField(auto_now=False)
    interests = models.CharField(max_length=5000)
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.user.first_name} {self.user.user.last_name}"

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

class InstAdmin(models.Model):
    user = models.OneToOneField(InstStaff, on_delete=models.DO_NOTHING)