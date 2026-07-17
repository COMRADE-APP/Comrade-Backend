from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import QNoteViewSet

router = DefaultRouter()
router.register(r'qnotes', QNoteViewSet, basename='qnote')

urlpatterns = [
    path('', include(router.urls)),
]
