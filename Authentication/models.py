from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from Institution.models import Institution, InstBranch
from Organisation.models import Organisation, OrgBranch
from django.contrib.auth.models import BaseUserManager
from datetime import datetime


USER_TYPE = (
    ('admin', 'Administrator (Comrade)'),
    ('staff', 'Staff'),
    ('lecturer', 'Lecturer'),
    ('student', 'Student'),
    ('moderator', 'Moderator'),
    ('student_admin', 'Student Admin'),
    ('institutional_admin', 'Institutional Admin'),
    ('institutional_staff', 'Institutional Staff'),
    ('organisational_admin', 'Organisational Admin'),
    ('organisational_staff', 'Organisational Staff'),
    ('author', 'Author'),
    ('editor', 'Editor'),
)


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
    is_student_admin = models.BooleanField(default=False)
    is_inst_admin = models.BooleanField(default=False)
    is_inst_staff = models.BooleanField(default=False)
    is_org_admin = models.BooleanField(default=False)
    is_org_staff = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_lecturer = models.BooleanField(default=False)
    is_student = models.BooleanField(default=True)
    is_moderator = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    
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
    
    def save(self, *args, **kwargs):
        self.user.is_student = True
        self.user.user_type = 'student'
        self.user.save()
        super().save(*args, **kwargs)


class StudentAdmin(models.Model):
    user = models.OneToOneField(Student, on_delete=models.DO_NOTHING)

    def save(self, *args, **kwargs):
        self.user.user.is_student_admin = True
        self.user.user.user_type = 'student_admin'
        self.user.user.save()
        super().save(*args, **kwargs)


class Lecturer(models.Model):   # FIXED
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    lecturer_id = models.CharField(max_length=200, unique=True, primary_key=True, default='LCT' )
    faculty = models.CharField(max_length=200, default='General')
    department = models.CharField(max_length=200, default='General')
    institution = models.OneToOneField(Institution, on_delete=models.DO_NOTHING, null=True)
    phone_number = models.CharField(max_length=15, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.user.is_lecturer = True
        self.user.user_type = 'lecturer'
        self.user.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"
    



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

    dob = models.DateField(auto_now_add=True)
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
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.user.is_org_staff = True
        self.user.user_type = 'organisational_staff'
        self.user.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"
    



class OrgAdmin(models.Model):
    user = models.OneToOneField(OrgStaff, on_delete=models.DO_NOTHING)

    def save(self, *args, **kwargs):
        self.user.user.is_org_admin = True
        self.user.user.user_type = 'organisational_admin'
        self.user.user.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.user.first_name} {self.user.user.last_name}"


class InstStaff(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.DO_NOTHING)
    institution = models.OneToOneField(Institution, on_delete=models.DO_NOTHING)
    inst_branch = models.OneToOneField(InstBranch, on_delete=models.DO_NOTHING)
    staff_id = models.CharField(max_length=200, unique=True, primary_key=True)
    staff_role = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    previous_institutions = models.ManyToManyField(
        Institution, related_name="previous_inst_admins")
    previous_inst_branch = models.ManyToManyField(
        InstBranch, related_name="previous_inst_branch_admins")
    dob = models.DateField(auto_now_add=True)
    interests = models.CharField(max_length=5000)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.user.user.is_inst_staff = True
        self.user.user.user_type = 'institutional_staff'
        self.user.user.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.user.first_name} {self.user.user.last_name}"

    

class InstAdmin(models.Model):
    user = models.OneToOneField(InstStaff, on_delete=models.DO_NOTHING)

    def save(self, *args, **kwargs):
        self.user.user.is_inst_admin = True
        self.user.user.user_type = 'institutional_admin'
        self.user.user.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.user.first_name} {self.user.user.last_name}"

    
class Profile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    bio = models.TextField(max_length=2000, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    cover_photo = models.ImageField(upload_to='cover_photos/', blank=True, null=True)
    location = models.CharField(max_length=300, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    blocked_users = models.ManyToManyField(CustomUser, related_name='blocked_by', blank=True)
    blocked_organizations = models.ManyToManyField(Organisation, related_name='orgs_blocked_by', blank=True)
    blocked_institutions = models.ManyToManyField(Institution, related_name='insts_blocked_by', blank=True)
    blocked_events = models.ManyToManyField('Events.Event', related_name='events_blocked_by', blank=True)
    blocked_rooms = models.ManyToManyField('Rooms.Room', related_name='rooms_blocked_by', blank=True)


    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} Profile"
    
class Author(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.DO_NOTHING)
    verified = models.BooleanField(default=False)
    created_on = models.DateTimeField(default=datetime.now)

    def save(self, *args, **kwargs):
        self.user.is_moderator = True
        self.user.user_type = 'author'
        self.user.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

class Editor(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.DO_NOTHING)
    verified = models.BooleanField(default=False)
    created_on = models.DateTimeField(default=datetime.now)

    def save(self, *args, **kwargs):
        self.user.is_moderator = True
        self.user.user_type = 'editor'
        self.user.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

class Moderator(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE)
    verified = models.BooleanField(default=False)
    created_on = models.DateTimeField(default=datetime.now)

    def save(self, *args, **kwargs):
        self.user.is_moderator = True
        self.user.user_type = 'moderator'
        self.user.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"