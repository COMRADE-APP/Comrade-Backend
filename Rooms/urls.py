from django.urls import path
from .views import *
from rest_framework.routers import DefaultRouter
from Rooms.views import RoomListCreateView, RoomDetailView, JoinRoomView, DefaultRoomViewSet, DirectMessageViewSet, DirectMessageRoomViewSet, ForwadingLogViewSet

routers = DefaultRouter()
routers.register(r'default_rooms', DefaultRoomViewSet, basename='default_rooms')
routers.register(r'direct_messages', DirectMessageViewSet, basename='direct_messages')
routers.register(r'direct_message_rooms', DirectMessageRoomViewSet, basename='direct_message_rooms')
routers.register(r'forwading_logs', ForwadingLogViewSet, basename='forwading_logs')



# urlpatterns = [
#     path('', RoomListCreateView.as_view(), name='room-list-create'),
#     path("<int:pk>/", RoomDetailView.as_view(), name='room_details' ),
#     path("join_room/", JoinRoomView.as_view(), name='join_room'),
# ]

urlpatterns = routers.urls