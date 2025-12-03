from rest_framework.permissions import BasePermission
from Authentication.models import Profile


class IsModerator(BasePermission):
    def has_object_permission(self, request, view, obj):
        profile = Profile.objects.get(user=request.user)

        return profile in (obj.moderator.all() or obj.admins.all() or obj.created_by.all())
    
    # def has_permission(self, request, view):
    #     return bool(request.user in (view.get_object().moderators.all(), view.get_object().admins.all(), view.get_object().created_by.all()))

class IsAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        profile = Profile.objects.get(user=request.user)

        return profile in obj.admins.all() 
    
class IsCreator(BasePermission):
    def has_object_permission(self, request, view, obj):
        profile = Profile.objects.get(user=request.user)

        return profile in  obj.created_by.all()
    
class IsMember(BasePermission):
    def has_object_permission(self, request, view, obj):
        profile = Profile.objects.get(user=request.user)

        return profile in obj.members.all()

