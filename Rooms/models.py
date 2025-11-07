from django.db import models
from Authentication.models import CustomUser, Student, StudentAdmin, OrgStaff, OrgAdmin, InstAdmin, InstBranch


from datetime import datetime
import uuid

# Create your models here.
class Room(models.Model):
    name = models.CharField(max_length=255)
    room_code = models.CharField(max_length=200, unique=True, editable=False, default=uuid.uuid4().hex)
    invitation_code = models.CharField(max_length=10, unique=True, editable=False)
    description = models.TextField(max_length=255, null=True)
    institution = models.CharField(max_length=255)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_on = models.DateTimeField(auto_now_add=True)
    members = models.ManyToManyField(CustomUser, related_name='joined_rooms', blank=True) # CustomUser can join many rooms, a room can have many CustomUsers

    def save(self, *args, **kwargs):
        if not self.invitation_code:
            self.invitation_code = self.generate_invitation_code()
        super().save(*args, **kwargs)
    
    def generate_invitation_code(self):
        return uuid.uuid4().hex[:10].upper()
    
    def __str__(self):
        return self.name
    
class DefaultRoom(models.Model):
    name = models.CharField(max_length=255)
    room_code = models.CharField(max_length=200, unique=True, default=uuid.uuid4().hex, editable=False)
    description = models.TextField(max_length=255, null=True)
    institution = models.CharField(max_length=255)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_on = models.DateTimeField(auto_now_add=True)
    members = models.ManyToManyField(CustomUser, related_name='joined_default_rooms', blank=True) # CustomUser can join many rooms, a room can have many CustomUsers
    invitation_code = models.CharField(max_length=10, unique=True, editable=False)
    def save(self, *args, **kwargs):
        if not self.invitation_code:
            self.invitation_code = self.generate_invitation_code()
        super().save(*args, **kwargs)
    def generate_invitation_code(self):
        return uuid.uuid4().hex[:10].upper()
    
    def __str__(self):
        return self.name


    
