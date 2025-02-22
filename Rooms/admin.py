from django.contrib import admin
from .models import Room

# Register your models here.
@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'invitation_code', 'created_by', 'description', 'institution']
    list_filter = ['name', 'created_by', 'institution']
    