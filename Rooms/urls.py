from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    RoomViewSet, 
    DefaultRoomViewSet, 
    DirectMessageViewSet, 
    DirectMessageRoomViewSet, 
    ForwadingLogViewSet,
    RoomListCreateView, 
    RoomDetailView, 
    JoinRoomView,
    TypingView
)

routers = DefaultRouter()
routers.register(r'rooms', RoomViewSet, basename='rooms')
routers.register(r'default_rooms', DefaultRoomViewSet, basename='default_rooms')
routers.register(r'direct_messages', DirectMessageViewSet, basename='direct_messages')
routers.register(r'dm_rooms', DirectMessageRoomViewSet, basename='dm_rooms')
routers.register(r'forwading_logs', ForwadingLogViewSet, basename='forwading_logs')

urlpatterns = [
    path('typing/<int:pk>/', TypingView.as_view(), name='typing'),
] + routers.urls