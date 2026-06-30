from rest_framework.permissions import BasePermission, SAFE_METHODS
from Authentication.models import Profile


class IsModerator(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return Profile.objects.filter(user=request.user).exists()

    def has_object_permission(self, request, view, obj):
        profile = Profile.objects.get(user=request.user)
        return profile in (obj.moderator.all() or obj.admins.all() or obj.created_by.all())


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return Profile.objects.filter(user=request.user).exists()

    def has_object_permission(self, request, view, obj):
        profile = Profile.objects.get(user=request.user)
        return profile in obj.admins.all()


class IsCreator(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return Profile.objects.filter(user=request.user).exists()

    def has_object_permission(self, request, view, obj):
        profile = Profile.objects.get(user=request.user)
        return profile in obj.created_by.all()


class IsMember(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return Profile.objects.filter(user=request.user).exists()

    def has_object_permission(self, request, view, obj):
        profile = Profile.objects.get(user=request.user)
        return profile in obj.members.all()
