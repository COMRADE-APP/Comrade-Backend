from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ResearchProjectViewSet, ParticipantPositionViewSet,
    ParticipantApplicationViewSet, RecruitmentPostViewSet,
    ResearcherApplicationViewSet, ResearchParticipantViewSet,
    PeerReviewViewSet, ResearchPublicationViewSet
)

router = DefaultRouter()
router.register(r'projects', ResearchProjectViewSet, basename='research-project')
router.register(r'positions', ParticipantPositionViewSet, basename='participant-position')
router.register(r'participants', ResearchParticipantViewSet, basename='research-participant')
router.register(r'reviews', PeerReviewViewSet, basename='peer-review')
router.register(r'publications', ResearchPublicationViewSet, basename='research-publication')
router.register(r'applications', ParticipantApplicationViewSet, basename='participant-application')
router.register(r'recruitment_posts', RecruitmentPostViewSet, basename='recruitment-post')
router.register(r'researcher_applications', ResearcherApplicationViewSet, basename='researcher-application')

urlpatterns = [
    path('', include(router.urls)),
]

