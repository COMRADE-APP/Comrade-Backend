from django.contrib import admin
from Rooms.models import Room, DefaultRoom, DirectMessage, DirectMessageRoom, ForwadingLog

# Register your models here.
admin.site.register(Room)
admin.register(DefaultRoom)
admin.register(DirectMessage)
admin.register(DirectMessageRoom)
admin.register(ForwadingLog)

class RoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'invitation_code', 'created_by', 'description', 'institution']
    list_filter = ['name', 'created_by', 'institution']
    