from django.db import models
from django.contrib.auth.models import User, AbstractUser
from django.contrib.auth.admin import UserAdmin
from Institution.models import Institution, Branch

import datetime

USER_TYPE = (
    ('admin', 'Administrator (Comrade)')
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
    first_name = models.CharField(max_length=200)
    middle_name = models.CharField(max_length=200, null=True, default='N/A')
    last_name = models.CharField(max_length=200)
    user_type = models.CharField(max_length=200, choices=USER_TYPE, default='student')
    email = models.EmailField(unique=True)

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    admission_number = models.CharField(max_length=100, unique=True)
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

