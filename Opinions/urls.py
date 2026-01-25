from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OpinionViewSet, FollowViewSet, BookmarkViewSet, BlockViewSet,
    UnifiedFeedView, NewContentCheckView
)

router = DefaultRouter()
router.register(r'opinions', OpinionViewSet, basename='opinion')
router.register(r'follow', FollowViewSet, basename='follow')
router.register(r'bookmarks', BookmarkViewSet, basename='bookmark')
router.register(r'block', BlockViewSet, basename='block')

urlpatterns = [
    path('feed/', UnifiedFeedView.as_view(), name='unified-feed'),
    path('feed/check-new/', NewContentCheckView.as_view(), name='check-new-content'),
    path('', include(router.urls)),
]
