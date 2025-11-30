from django.contrib import admin
from Specialization.models import Specialization, Stack, SavedSpecialization, SavedStack, SpecializationAdmin, SpecializationMembership, SpecializationModerator, SpecializationRoom, StackAdmin, StackMembership, StackModerator, CompletedSpecialization, CompletedStack, PositionTracker

# Register your models here.
admin.site.register(Specialization)
admin.site.register(Stack)
admin.site.register(SavedSpecialization)
admin.site.register(SavedStack)
admin.site.register(SpecializationAdmin)
admin.site.register(SpecializationMembership)
admin.site.register(SpecializationModerator)
admin.site.register(SpecializationRoom)
admin.site.register(StackAdmin)
admin.site.register(StackMembership)
admin.site.register(StackModerator)
admin.site.register(CompletedSpecialization)
admin.site.register(CompletedStack)
admin.site.register(PositionTracker)

