from django.db import models
from django.contrib.auth.models import User
import uuid

# Create your models here.
class Room(models.Model):
    name = models.CharField(max_length=255)
    invitation_code = models.CharField(max_length=10, unique=True, editable=False)
    description = models.TextField(max_length=255, null=True)
    institution = models.CharField(max_length=255)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_on = models.DateTimeField(auto_now_add=True)
    members = models.ManyToManyField(User, related_name='joined_rooms', blank=True) # user can join many rooms, a room can have many users.

    def save(self, *args, **kwargs):
        if not self.invitation_code:
            self.invitation_code = self.generate_invitation_code()
        super().save(*args, **kwargs)
    
    def generate_invitation_code(self):
        return uuid.uuid4().hex[:10].upper()
    
    def __str__(self):
        return self.name
