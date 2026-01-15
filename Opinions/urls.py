from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OpinionViewSet, FollowViewSet, BookmarkViewSet

router = DefaultRouter()
router.register(r'opinions', OpinionViewSet, basename='opinion')
router.register(r'follow', FollowViewSet, basename='follow')
router.register(r'bookmarks', BookmarkViewSet, basename='bookmark')

urlpatterns = [
    path('', include(router.urls)),
]
