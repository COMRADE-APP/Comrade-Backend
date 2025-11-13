from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from Resources.models import Resource, ResourceVisibility
from Resources.serializers import ResourceSerializer, ResourceVisibilitySerializer
from Rooms.models import Room, DefaultRoom
from Rooms.serializers import RoomSerializer, DefaultRoomSerializer
from Announcements.models import AnnouncementsRequest, Announcements, Task, Text, CompletedTask, Pin, Reposts, Reply, QuestionResponse, Question, SubQuestion, Choice, FileResponse, TaskResponse
from Organisation.models import Organisation, OrgBranch, Division, Department, Section, Team, Project, Centre, Committee, Board, Unit, Institute, Program
from Institution.models import Institution, InstBranch, VCOffice, Faculty, InstDepartment, AdminDep, Library, Hostel, Cafeteria, Programme, HR, Admissions, HealthServices, Security, StudentAffairs, SupportServices, Finance, Marketing, Legal, ICT, CareerOffice, Counselling, RegistrarOffice, Transport
from Rooms.permissions import IsModerator
from Announcements.serializers import AnnouncementsSerializer, TaskSerializer, FileResponseSerializer, TextSerializer, CompletedTaskSerializer, PinSerializer, RepostsSerializer, ReplySerializer, QuestionResponseSerializer, QuestionSerializer, SubQuestionSerializer, ChoiceSerializer, TaskResponseSerializer
from Authentication.models import CustomUser as User, Student, StudentAdmin, Lecturer, InstAdmin, InstStaff, OrgAdmin, OrgStaff
from Authentication.serializers import CustomUserSerializer, StudentSerializer, StudentAdminSerializer, LecturerSerializer, InstAdminSerializer, InstStaffSerializer, OrgAdminSerializer, OrgStaffSerializer



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
    
    @action(detail=True, methods=['get', 'post', 'delete', 'put', 'patch'])
    def resources(self, request, pk=None):
        room = self.get_object()
        if request.method == 'GET':
            resources = FileResponse.objects.filter(room=room)
            serializer = FileResponseSerializer(resources, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        # Check if user has permission to upload/edit/delete resources
        permissions = IsModerator()
        if permissions.has_permission(request, self):
        # elif request.user.is_student_admin or request.user.is_inst_admin or request.user.is_org_admin or request.user.is_admin or request.user.is_moderator:
            if request.method == 'POST':
                serializer = FileResponseSerializer(data=request.data)
                if serializer.is_valid():
                    serializer.save(room=room, uploaded_by=request.user)
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            elif request.method in ['PUT', 'PATCH']:
                resource_id = request.data.get('id')
                resource = get_object_or_404(FileResponse, id=resource_id, room=room)
                serializer = FileResponseSerializer(resource, data=request.data, partial=(request.method == 'PATCH'))
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            elif request.method == 'DELETE':
                resource_id = request.data.get('id')
                resource = get_object_or_404(FileResponse, id=resource_id, room=room)
                resource.delete()
                return Response({"message": "Resource deleted successfully."}, status=status.HTTP_200_OK)
        # Deny if user lacks permission
        else:
            return Response({"message": "You do not have permission to upload or edit resources to this room."}, status=status.HTTP_403_FORBIDDEN)
        
    @action(detail=True, methods=['get'])
    def resources_count(self, request, pk=None):
        room = self.get_object()
        resources_count = FileResponse.objects.filter(room=room).count()
        return Response({"resources_count": resources_count}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get', 'post'])
    def change_resource_visibility(self, request, pk=None):
        room = self.get_object()
        if request.method == 'GET':
            visibilities = ResourceVisibility.objects.filter(room=room)
            serializer = ResourceVisibilitySerializer(visibilities, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif request.method == 'POST' and request.user.is_student_admin or request.user.is_inst_admin or request.user.is_org_admin or request.user.is_admin:
            serializer = ResourceVisibilitySerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(room=room, created_by=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"message": "You do not have permission to change resource visibility."}, status=status.HTTP_403_FORBIDDEN)
    
    @action(detail=True, methods=['get', 'post'])
    def default_rooms(self, request, pk=None):
        room = self.get_object()
        if request.method == 'GET':
            default_rooms = DefaultRoom.objects.filter(members=room)
            serializer = DefaultRoomSerializer(default_rooms, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif request.method == 'POST':
            serializer = DefaultRoomSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(members=room, created_by=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get', 'post'])
    def make_moderator(self, request, pk=None):
        room = self.get_object()
        if request.method == 'POST' and request.user.is_student_admin or request.user.is_inst_admin or request.user.is_org_admin or request.user.is_admin:
            user_id = request.data.get('user_id')
            user = get_object_or_404(User, id=user_id)
            room.moderators.add(user)
            return Response({"message": "User has been made a moderator."}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "You do not have permission to make moderators."}, status=status.HTTP_403_FORBIDDEN)
    
    @action(detail=True, methods=['get', 'post'])
    def remove_moderator(self, request, pk=None):
        room = self.get_object()
        if request.method == 'POST' and request.user.is_student_admin or request.user.is_inst_admin or request.user.is_org_admin or request.user.is_admin:
            user_id = request.data.get('user_id')
            user = get_object_or_404(User, id=user_id)
            room.moderators.remove(user)
            return Response({"message": "User has been removed from moderators."}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "You do not have permission to remove moderators."}, status=status.HTTP_403_FORBIDDEN)
        
    @action(detail=True, methods=['get'])
    def moderators(self, request, pk=None):
        room = self.get_object()
        moderators = room.moderators.all()
        moderator_usernames = [moderator.username for moderator in moderators]
        return Response({"moderators": moderator_usernames}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get', 'post'])
    def make_admin(self, request, pk=None):
        room = self.get_object()
        if request.method == 'POST' and request.user.is_student_admin or request.user.is_inst_admin or request.user.is_org_admin or request.user.is_admin:
            user_id = request.data.get('user_id')
            user = get_object_or_404(User, id=user_id)
            room.members.add(user)  # Ensure the new admin is also a member
            room.admins.add(user)
            room.save()
            return Response({"message": "User has been made the room admin."}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "You do not have permission to make room admins."}, status=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=['get', 'post'])
    def remove_admin(self, request, pk=None):
        room = self.get_object()
        if request.method == 'POST' and request.user.is_student_admin or request.user.is_inst_admin or request.user.is_org_admin or request.user.is_admin:
            user_id = request.data.get('user_id')
            user = get_object_or_404(User, id=user_id)
            room.admins.remove(user)
            room.save()
            return Response({"message": "User has been removed from room admins."}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "You do not have permission to remove room admins."}, status=status.HTTP_403_FORBIDDEN)
        
    @action(detail=True, methods=['get', 'post'])
    def add_member(self, request, pk=None):
        room = self.get_object()
        if request.method == 'POST' and request.user.is_student_admin or request.user.is_inst_admin or request.user.is_org_admin or request.user.is_admin:
            user_id = request.data.get('user_id')
            user = get_object_or_404(User, id=user_id)
            room.members.add(user)
            return Response({"message": "User has been added to the room."}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "You do not have permission to add members to this room."}, status=status.HTTP_403_FORBIDDEN)
    
    @action(detail=True, methods=['get', 'post'])
    def remove_member(self, request, pk=None):
        room = self.get_object()
        if request.method == 'POST' and request.user.is_student_admin or request.user.is_inst_admin or request.user.is_org_admin or request.user.is_admin:
            user_id = request.data.get('user_id')
            user = get_object_or_404(User, id=user_id)
            room.members.remove(user)
            return Response({"message": "User has been removed from the room."}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "You do not have permission to remove members from this room."}, status=status.HTTP_403_FORBIDDEN)
    
    @action(detail=True, methods=['get', 'post'])
    def convert_to_default_room(self, request, pk=None):
        room = self.get_object()
        if request.method == 'POST' and request.user.is_student_admin or request.user.is_inst_admin or request.user.is_org_admin or request.user.is_admin:
            default_room = DefaultRoom.objects.create(name=room.name, description=room.description, created_by=request.user)
            default_room.members.set(room.members.all())
            default_room.save()
            return Response({"message": "Room has been converted to a default room."}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "You do not have permission to convert this room to a default room."}, status=status.HTTP_403_FORBIDDEN)
        
    

class DefaultRoomViewSet(ModelViewSet):
    queryset = DefaultRoom.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DefaultRoomSerializer

    @action(detail=True, methods=['get', 'post'])
    def convert_from_default_room(self, request, pk=None):
        room = self.get_object()
        if request.method == 'POST' and request.user.is_student_admin or request.user.is_inst_admin or request.user.is_org_admin or request.user.is_admin:
            default_room = DefaultRoom.objects.create(name=room.name, description=room.description, created_by=request.user)
            default_room.members.set(room.members.all())
            default_room.save()
            return Response({"message": "Default room has been converted to a room."}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "You do not have permission to convert this default room to a room."}, status=status.HTTP_403_FORBIDDEN)