from rest_framework import generics, permissions
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from .models import Room
from .serializers import RoomSerializer

class RoomListCreateView(generics.ListCreateAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        response = serializer.save()
        return response
    
class RoomDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_update(self, serializer):
        response = serializer.save()
        return response
    
    def perform_destroy(self, instance):
        response = instance.delete()
        return response

class JoinRoomView(APIView):
    def post(self, request):
        invitation_code = request.data.get("invitation_code")
        user = request.user

        room = get_object_or_404(Room, invitation_code=invitation_code)

        if user in room.members.all():
            return Response({"message": "user already exists in the room."}, status=status.HTTP_400_BAD_REQUEST)
        
        room.members.add(user)
        return Response({"message": "Successfully joined the room."}, status=status.HTTP_200_OK)