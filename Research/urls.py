from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ResearchProjectViewSet, ParticipantPositionViewSet,
    ResearchParticipantViewSet, PeerReviewViewSet, ResearchPublicationViewSet
)

router = DefaultRouter()
router.register(r'projects', ResearchProjectViewSet, basename='research-project')
router.register(r'positions', ParticipantPositionViewSet, basename='participant-position')
router.register(r'participants', ResearchParticipantViewSet, basename='research-participant')
router.register(r'reviews', PeerReviewViewSet, basename='peer-review')
router.register(r'publications', ResearchPublicationViewSet, basename='research-publication')

urlpatterns = [
    path('', include(router.urls)),
]
