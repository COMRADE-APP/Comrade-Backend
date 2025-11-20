from rest_framework.permissions import BasePermission
from Rooms.permissions import IsModerator
from Resources.models import Resource

class IsAuthor(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.created_by == request.user

class IsEditor(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user in obj.editors.all()

class IsAuthorOrEditor(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.created_by == request.user or request.user in obj.editors.all()