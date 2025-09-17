from django.db import models
from rest_framework.exceptions import ValidationError
from Rooms.models import Room


# Resource types
RESOURCE_TYPES = (
    ('media_link', 'Media Link'),
    ('text', 'Text'),
    ('image', 'Image file'),
    ('doc', 'Document File'),
)
VIS_TYPES = (
    ('public', 'Public'),
    ('private', 'Private'),
    ('only_me', 'Only Me'),
    ('course', 'Your Course or Class'),
    ('faculty', 'Your Faculty or School'),
    ('institutional', 'Your Institution'),
    ('organisational', 'Your Organisation'),
    ('group', 'Your Group or Section')
)
class Resource(models.Model):
    visibility = models.CharField(max_length=20, choices=VIS_TYPES, default='public')
    title = models.CharField(max_length=100, default='', )
    desc = models.TextField(max_length=1000, default='')
    file_type = models.CharField(max_length=20, choices=RESOURCE_TYPES, default='doc')
    res_file = models.FileField(upload_to="uploads/", blank=True, null=True)
    res_text = models.TextField(max_length=50000, blank=True, null=True)

    def clean(self):
        """Custom validation to ensure correct field usage."""
        if self.file_type == "text" and not self.res_text:
            raise ValidationError("Text resource requires res_text content.")
        if self.file_type in ["image", "doc"] and not self.res_file:
            raise ValidationError("File upload is required for this type.")
        if self.file_type == "media_link" and not isinstance(self.res_file, str):
            raise ValidationError("Media Link should be a valid URL.")

    def save(self, *args, **kwargs):
        """Override save method to ensure correct field is used."""
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
    
class ResourceVisibility(models.Model):
    resource = models.OneToOneField(Resource, on_delete=models.CASCADE)
    room = models.OneToOneField(Room, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now=True)
    # created_by = models.OneToOneField(User, on_delete=models.DO_NOTHING, null=False)