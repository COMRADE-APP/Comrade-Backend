from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from Rooms.models import Room, DefaultRoom
from Rooms.serializers import RoomSerializer, DefaultRoomSerializer
from Announcements.models import AnnouncementsRequest, Announcements, Task, Text, CompletedTask, Pin, Reposts, Reply, QuestionResponse, Question, SubQuestion, Choice, FileResponse
from Organisation.models import Organisation, OrgBranch, Division, Department, Section, Team, Project, Centre, Committee, Board, Unit, Institute, Program
from Institution.models import Institution, InstBranch, VCOffice, Faculty, InstDepartment, AdminDep, Library, Hostel, Cafeteria, Programme, HR, Admissions, HealthServices, Security, StudentAffairs, SupportServices, Finance, Marketing, Legal, ICT, CareerOffice, Counselling, RegistrarOffice, Transport


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
    
class RoomViewSet(ModelViewSet):
    queryset = Room.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RoomSerializer

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        room = self.get_object()
        user = request.user

        if user in room.members.all():
            return Response({"message": "user already exists in the room."}, status=status.HTTP_400_BAD_REQUEST)
        
        room.members.add(user)
        return Response({"message": "Successfully joined the room."}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        room = self.get_object()
        user = request.user

        if user not in room.members.all():
            return Response({"message": "user is not a member of the room."}, status=status.HTTP_400_BAD_REQUEST)
        
        room.members.remove(user)
        return Response({"message": "Successfully left the room."}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        room = self.get_object()
        members = room.members.all()
        member_usernames = [member.username for member in members]
        return Response({"members": member_usernames}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def member_count(self, request, pk=None):
        room = self.get_object()
        member_count = room.members.count()
        return Response({"member_count": member_count}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get', 'post'])
    def announcements(self, request, pk=None):
        room = self.get_object()
        if request.method == 'GET':
            announcements = Announcements.objects.filter(room=room)
            serializer = AnnouncementsSerializer(announcements, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif request.method == 'POST' and request.user.is_student_admin or request.user.is_inst_admin or request.user.is_org_admin or request.user.is_admin:
            serializer = AnnouncementsSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(room=room, created_by=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"message": "You do not have permission to create announcements."}, status=status.HTTP_403_FORBIDDEN)
        
    @action(detail=True, methods=['get', 'post'])
    def tasks(self, request, pk=None):
        room = self.get_object()
        if request.method == 'GET':
            tasks = Task.objects.filter(room=room)
            serializer = TaskSerializer(tasks, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif request.method == 'POST' and request.user.is_student_admin or request.user.is_inst_admin or request.user.is_org_admin or request.user.is_admin:
            serializer = TaskSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(room=room, created_by=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"message": "You do not have permission to create tasks."}, status=status.HTTP_403_FORBIDDEN)
    
    @action(detail=True, methods=['get'])
    def tasks_count(self, request, pk=None):
        room = self.get_object()
        tasks_count = Task.objects.filter(room=room).count()
        return Response({"tasks_count": tasks_count}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def announcements_count(self, request, pk=None):
        room = self.get_object()
        announcements_count = Announcements.objects.filter(room=room).count()
        return Response({"announcements_count": announcements_count}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get', 'post'])
    def resources(self, request, pk=None):
        room = self.get_object()
        if request.method == 'GET':
            resources = FileResponse.objects.filter(room=room)
            serializer = FileResponseSerializer(resources, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif request.method == 'POST' and request.user.is_student_admin or request.user.is_inst_admin or request.user.is_org_admin or request.user.is_admin:
            serializer = FileResponseSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(room=room, uploaded_by=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"message": "You do not have permission to upload resources."}, status=status.HTTP_403_FORBIDDEN)

class DefaultRoomViewSet(ModelViewSet):
    queryset = DefaultRoom.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DefaultRoomSerializer