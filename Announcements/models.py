from django.db import models
from datetime import datetime
from Authentication.models import StudentAdmin
from django.contrib.auth.models import User
from Authentication.models import Student
# Create your models here.

ANN_STATUS = (
    ('pending', 'Pending'),
    ('scheduled', 'Scheduled'),
    ('sent', 'Sent'),
    ('not_sent', 'Not Sent')
)

class Text(models.Model):
    user = models.OneToOneField(Student, on_delete=models.DO_NOTHING)
    content = models.CharField(max_length=5000, null=False)
    status = models.CharField(max_length=200, choices=ANN_STATUS, 
    default='pending')
    time_stamp = models.DateTimeField(default=datetime.now())
    # source = models.OneToOneField(User, on_delete=models.DO_NOTHING)

class Reply(models.Model):
    reference_text = models.OneToOneField(Text, on_delete=models.DO_NOTHING)
    user = models.OneToOneField(Student, on_delete=models.DO_NOTHING)
    content = models.CharField(max_length=5000, null=False)
    status = models.CharField(max_length=200, choices=ANN_STATUS, 
    default='pending')
    time_stamp = models.DateTimeField(default=datetime.now())



class Announcements(models.Model):
    user = models.OneToOneField(StudentAdmin, on_delete=models.DO_NOTHING)
    heading = models.CharField(max_length=200, null=False)
    content = models.TextField(max_length=5000, null=False)
    time_stamp = models.DateTimeField(default=datetime.now())
    status = models.CharField(max_length=200, choices=ANN_STATUS, 
    default='pending')
