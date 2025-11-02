from django.urls import path, include
from Announcements.views import AnnouncementsViewSet, TextViewSet, ReplyViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'announcements', AnnouncementsViewSet, basename='announcement')
router.register(r'texts', TextViewSet, basename='text')
router.register(r'replies', ReplyViewSet, basename='reply')

urlpatterns = [
    path('', include(router.urls)),
]