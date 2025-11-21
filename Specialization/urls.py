from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Specialization.views import SpecializationViewSet, StackViewSet, SavedSpecializationViewSet, SavedStackViewSet, SpecializationAdminViewSet, SpecializationMembershipViewSet, SpecializationModeratorViewSet, SpecializationRoomViewSet, StackAdminViewSet, StackMembershipViewSet, StackModeratorViewSet, CompletedSpecializationViewSet, CompletedStackViewSet


router = DefaultRouter()

router.register(r'specializations', SpecializationViewSet, basename='specialization')
router.register(r'stacks', StackViewSet, basename='stack')
router.register(r'saved_specializations', SavedSpecializationViewSet, basename='saved_specialization')
router.register(r'saved_stacks', SavedStackViewSet, basename='saved_stack')
router.register(r'completed_specializations', CompletedSpecializationViewSet, basename='completed_specialization')
router.register(r'completed_stacks', CompletedStackViewSet, basename='completed_stack')
router.register(r'specialization_admins', SpecializationAdminViewSet, basename='specialization_admin')
router.register(r'stack_admins', StackAdminViewSet, basename='stack_admin')
router.register(r'specialization_moderators', SpecializationModeratorViewSet, basename='specialization_moderator')
router.register(r'stack_moderators', StackModeratorViewSet, basename='stack_moderator')
router.register(r'specialization_memberships', SpecializationMembershipViewSet, basename='specialization_membership')
router.register(r'stack_memberships', StackMembershipViewSet, basename='stack_membership')
router.register(r'specialization_rooms', SpecializationRoomViewSet, basename='specialization_room')



urlpatterns = []

urlpatterns += router.urls




