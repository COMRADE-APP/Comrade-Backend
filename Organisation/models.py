from django.db import models

# Create your models here.
class Organisation(models.Model):
    name = models.CharField(max_length=1000)
    origin = models.CharField(max_length=500)
    abbreviation = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    postal_code = models.CharField(max_length=200)
    town = models.CharField(max_length=100)
    city = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now=True)

class Branch(models.Model):
    Organisation = models.OneToOneField(Organisation, on_delete=models.DO_NOTHING)
    name = models.CharField(max_length=200)
    branch_code = models.CharField(max_length=200, unique=True, primary_key=True)
    origin = models.CharField(max_length=500)
    abbreviation = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    postal_code = models.CharField(max_length=200)
    town = models.CharField(max_length=100)
    city = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now=True)