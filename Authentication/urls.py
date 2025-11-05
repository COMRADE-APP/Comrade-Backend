from django.urls import path
from Authentication.views import RegisterView, LoginView, CustomUserViewSet, LecturerViewSet, OrgStaffViewSet, StudentAdminViewSet, OrgAdminViewSet, InstAdminViewSet, InstStaffViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
# router.register(r'students', StudentViewSet, basename='student')
router.register(r'custom_users', CustomUserViewSet, basename='custom_user')
router.register(r'lecturers', LecturerViewSet, basename='lecturer')
router.register(r'org_staffs', OrgStaffViewSet, basename='org_staff')
router.register(r'student_admins', StudentAdminViewSet, basename='student_admin')
router.register(r'org_admins', OrgAdminViewSet, basename='org_admin')
router.register(r'inst_admins', InstAdminViewSet, basename='inst_admin')
router.register(r'inst_staffs', InstStaffViewSet, basename='inst_staff')


urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name = 'login'),
]
urlpatterns += router.urls

