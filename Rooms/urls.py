from django.urls import path
from .views import *

urlpatterns = [
    path('', RoomListCreateView.as_view(), name='room-list-create'),
    path("<int:pk>/", RoomDetailView.as_view(), name='room_details' )
]