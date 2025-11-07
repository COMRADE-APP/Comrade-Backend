from rest_framework.permissions import IsAdminUser, IsAuthenticated, IsAuthenticatedOrReadOnly, BasePermission


class IsInstAdminUser(IsAuthenticated):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_inst_admin)
    
class IsOrgAdminUser(IsAuthenticated):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_org_admin)
    
class IsStudentAdminUser(IsAuthenticated):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_student_admin)
    
class IsOrgStaffUser(IsAuthenticated):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_org_staff)
    
class IsStudentUser(IsAuthenticated):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_student)
    
class IsRoomMember(IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        return bool(request.user and request.user.is_authenticated and request.user in obj.members.all())
    
class IsRoomAdminUser(IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        return bool(request.user and request.user.is_authenticated and request.user == obj.created_by)
    
class IsRoomMemberOrReadOnly(IsAuthenticatedOrReadOnly):
    def has_object_permission(self, request, view, obj):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        return bool(request.user and request.user.is_authenticated and request.user in obj.members.all())
    
class IsAdmin(IsAuthenticated):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)