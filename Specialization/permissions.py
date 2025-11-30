from rest_framework.permissions import BasePermission
from Authentication.models import Profile


class IsModerator(BasePermission):
    def has_object_permission(self, request, view, obj):
        profile = Profile.objects.get(user=request.user)

        return profile in obj.moderators.all() 

class IsAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        profile = Profile.objects.get(user=request.user)

        return profile in obj.admins.all() 
    
class IsCreator(BasePermission):
    def has_object_permission(self, request, view, obj):
        profile = Profile.objects.get(user=request.user)

        return profile == obj.created_by


