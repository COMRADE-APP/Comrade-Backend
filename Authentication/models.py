from django.db import models
from django.contrib.auth.models import User

import datetime

# Create your models here
class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    admission_number = models.CharField(max_length=100, unique=True)
    year_of_admission = models.IntegerField()
    faculty = models.CharField(max_length= 200)
    course = models.CharField(max_length= 200)
    institution = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=15)
    password = models.CharField(max_length=200)

    def __str__(self):
        return self.user.first_name + " " + self.user.last_name

    