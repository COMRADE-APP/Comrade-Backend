from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Specialization.views import (
    SpecializationViewSet, StackViewSet,
    SavedSpecializationViewSet, SavedStackViewSet,
    SpecializationAdminViewSet, SpecializationMembershipViewSet,
    SpecializationModeratorViewSet, SpecializationRoomViewSet,
    StackAdminViewSet, StackMembershipViewSet, StackModeratorViewSet,
    CompletedSpecializationViewSet, CompletedStackViewSet,
    PositionTrackerViewSet, CertificateViewSet, IssuedCertificateViewSet,
    LessonViewSet, QuizViewSet, QuizQuestionViewSet,
    EnrollmentViewSet, LearnerProgressViewSet
)

router = DefaultRouter()

# Core LMS
router.register(r'specializations', SpecializationViewSet, basename='specialization')
router.register(r'stacks', StackViewSet, basename='stack')
router.register(r'lessons', LessonViewSet, basename='lesson')
router.register(r'quizzes', QuizViewSet, basename='quiz')
router.register(r'quiz-questions', QuizQuestionViewSet, basename='quiz-question')
router.register(r'enrollments', EnrollmentViewSet, basename='enrollment')
router.register(r'progress', LearnerProgressViewSet, basename='progress')

# Certificates
router.register(r'certificates', CertificateViewSet, basename='certificate')
router.register(r'issued_certificates', IssuedCertificateViewSet, basename='issued_certificate')

# Saved & Completed
router.register(r'saved_specializations', SavedSpecializationViewSet, basename='saved_specialization')
router.register(r'saved_stacks', SavedStackViewSet, basename='saved_stack')
router.register(r'completed_specializations', CompletedSpecializationViewSet, basename='completed_specialization')
router.register(r'completed_stacks', CompletedStackViewSet, basename='completed_stack')

# Admin & Moderation
router.register(r'specialization_admins', SpecializationAdminViewSet, basename='specialization_admin')
router.register(r'stack_admins', StackAdminViewSet, basename='stack_admin')
router.register(r'specialization_moderators', SpecializationModeratorViewSet, basename='specialization_moderator')
router.register(r'stack_moderators', StackModeratorViewSet, basename='stack_moderator')
router.register(r'specialization_memberships', SpecializationMembershipViewSet, basename='specialization_membership')
router.register(r'stack_memberships', StackMembershipViewSet, basename='stack_membership')
router.register(r'specialization_rooms', SpecializationRoomViewSet, basename='specialization_room')
router.register(r'position_trackers', PositionTrackerViewSet, basename='position_tracker')

urlpatterns = router.urls
