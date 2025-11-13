from django.contrib import admin
from .models import Room, DefaultRoom

# Register your models here.
admin.site.register(Room)
admin.register(DefaultRoom)

class RoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'invitation_code', 'created_by', 'description', 'institution']
    list_filter = ['name', 'created_by', 'institution']
    