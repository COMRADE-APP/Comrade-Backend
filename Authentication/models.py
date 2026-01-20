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
    ('normal_user', 'Normal User'),  # Non-student general users
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
    other_names = models.CharField(max_length=200, null=True, default='N/A')
    last_name = models.CharField(max_length=200)
    user_type = models.CharField(max_length=200, choices=USER_TYPE, default='student')
    phone_number = models.CharField(max_length=15, default='0123456789')
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
    is_author = models.BooleanField(default=False)
    is_editor = models.BooleanField(default=False)
    is_normal_user = models.BooleanField(default=False)  # Non-student general users
    
    # Profile completion tracking
    profile_completed = models.BooleanField(default=False)
    
    # Login OTP (email verification on login)
    login_otp = models.CharField(max_length=6, blank=True, null=True)
    login_otp_expires = models.DateTimeField(null=True, blank=True)
    
    # Password Reset OTP
    password_reset_otp_secret = models.CharField(max_length=32, blank=True, null=True)
    password_reset_otp_expires = models.DateTimeField(null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = CustomUserManager()
    
    class Meta:
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['user_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['email', 'is_active']),
        ]


class Student(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    admission_number = models.CharField(max_length=100, unique=True, primary_key=True)
    year_of_admission = models.IntegerField(default=2000)
    year_of_study = models.IntegerField(default=1)
    current_semester = models.IntegerField(default=1)
    institution = models.CharField(max_length=2000)
    faculty = models.CharField(max_length=2000)
    course = models.CharField(max_length=2000)
    expecte_year_of_graduation = models.IntegerField(default=2000)
    created_on = models.DateField(default=datetime.now)

    def __str__(self):
        return f"{self.admission_number}---{self.user.first_name} {self.user.last_name}"
    
    def save(self, *args, **kwargs):
        self.user.is_student = True
        self.user.user_type = 'student'
        self.user.save()
        super().save(*args, **kwargs)


class StudentAdmin(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE)
    created_on = models.DateTimeField(default=datetime.now)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.student.user.is_student_admin = True
        self.student.user.user_type = 'student_admin'
        self.student.user.save()
        super().save(*args, **kwargs)


class Lecturer(models.Model):   # FIXED
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    lecturer_id = models.CharField(max_length=200, unique=True, primary_key=True, default='LCT' )
    faculty = models.CharField(max_length=200, default='General')
    department = models.CharField(max_length=200, default='General')
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, null=True)
    created_at = models.DateTimeField(default=datetime.now)

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

    current_organisation = models.ForeignKey(
        Organisation, on_delete=models.CASCADE, null=True,
        related_name="current_staff"
    )
    current_org_branch = models.ForeignKey(
        OrgBranch, on_delete=models.CASCADE, null=True,
        related_name="current_branch_staff"
    )
    previous_organisations = models.ManyToManyField(
        Organisation, related_name="previous_staff"
    )
    previous_org_branch = models.ManyToManyField(
        OrgBranch, related_name="previous_branch_staff"
    )

    dob = models.DateField(default=datetime.now)
    nationality = models.CharField(max_length=300)
    country_of_residence = models.CharField(max_length=300)

    current_institution = models.ForeignKey(
        Institution, on_delete=models.CASCADE, null=True,
        related_name="current_inst_staff"
    )
    current_inst_branch = models.ForeignKey(
        InstBranch, on_delete=models.CASCADE, null=True,
        related_name="current_inst_branch_staff"
    )
    previous_institutions = models.ManyToManyField(
        Institution, related_name="previous_inst_staff"
    )
    previous_inst_branch = models.ManyToManyField(
        InstBranch, related_name="previous_inst_branch_staff"
    )

    interests = models.CharField(max_length=5000)
    created_at = models.DateTimeField(default=datetime.now)

    def save(self, *args, **kwargs):
        self.user.is_org_staff = True
        self.user.user_type = 'organisational_staff'
        self.user.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"
    



class OrgAdmin(models.Model):
    staff = models.OneToOneField(OrgStaff, on_delete=models.CASCADE)
    created_on = models.DateTimeField(default=datetime.now)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.staff.user.is_org_admin = True
        self.staff.user.user_type = 'organisational_admin'
        self.staff.user.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.staff.user.first_name} {self.staff.user.last_name}"


class InstStaff(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE)
    inst_branch = models.ForeignKey(InstBranch, on_delete=models.CASCADE)
    staff_id = models.CharField(max_length=200, unique=True, primary_key=True)
    staff_role = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    previous_institutions = models.ManyToManyField(
        Institution, related_name="previous_inst_admins")
    previous_inst_branch = models.ManyToManyField(
        InstBranch, related_name="previous_inst_branch_admins")
    dob = models.DateField(default=datetime.now)
    interests = models.CharField(max_length=5000)
    created_at = models.DateTimeField(default=datetime.now)

    def save(self, *args, **kwargs):
        self.user.is_inst_staff = True
        self.user.user_type = 'institutional_staff'
        self.user.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

    

class InstAdmin(models.Model):
    staff = models.OneToOneField(InstStaff, on_delete=models.CASCADE)
    created_on = models.DateTimeField(default=datetime.now)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.staff.user.is_inst_admin = True
        self.staff.user.user_type = 'institutional_admin'
        self.staff.user.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.staff.user.first_name} {self.staff.user.last_name}"

    
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
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    verified = models.BooleanField(default=False)
    created_on = models.DateTimeField(default=datetime.now)

    def save(self, *args, **kwargs):
        self.user.is_author = True
        self.user.user_type = 'author'
        self.user.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

class Editor(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    verified = models.BooleanField(default=False)
    created_on = models.DateTimeField(default=datetime.now)

    def save(self, *args, **kwargs):
        self.user.is_editor = True
        self.user.user_type = 'editor'
        self.user.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

class Moderator(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    verified = models.BooleanField(default=False)
    created_on = models.DateTimeField(default=datetime.now)

    def save(self, *args, **kwargs):
        self.user.is_moderator = True
        self.user.user_type = 'moderator'
        self.user.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"
    
class ComradeAdmin(models.Model):
    """
    Platform super-admin with full access. Linking to CustomUser and
    ensuring relevant flags (is_admin/is_staff/is_superuser) are set on save.
    """
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    created_on = models.DateTimeField(default=datetime.now)
    created_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_comrade_admins'
    )

    def save(self, *args, **kwargs):
        # Ensure this user has full admin privileges across the platform
        self.user.is_admin = True
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.is_active = True
        self.user.user_type = 'admin'
        self.user.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} (ComradeAdmin)"


class NormalUser(models.Model):
    """
    Profile extension for non-student general users.
    Allows platform access without student-specific requirements.
    """
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    occupation = models.CharField(max_length=300, blank=True)
    interests = models.TextField(blank=True)
    created_on = models.DateTimeField(default=datetime.now)

    def save(self, *args, **kwargs):
        self.user.is_normal_user = True
        self.user.is_student = False
        self.user.user_type = 'normal_user'
        self.user.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} (Normal User)"


ROLE_CHANGE_STATUS = (
    ('pending', 'Pending Review'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('cancelled', 'Cancelled'),
)

class RoleChangeRequest(models.Model):
    """
    Model for users to request a change in their user type/role.
    Requires admin review and approval.
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='role_change_requests')
    current_role = models.CharField(max_length=100)
    requested_role = models.CharField(max_length=100, choices=USER_TYPE)
    reason = models.TextField(help_text="Explain why you need this role change")
    supporting_documents = models.FileField(upload_to='role_requests/', blank=True, null=True)
    status = models.CharField(max_length=50, choices=ROLE_CHANGE_STATUS, default='pending')
    reviewed_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_role_requests'
    )
    review_notes = models.TextField(blank=True, null=True)
    created_on = models.DateTimeField(default=datetime.now)
    reviewed_on = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_on']

    def __str__(self):
        return f"{self.user.email}: {self.current_role} -> {self.requested_role} ({self.status})"

