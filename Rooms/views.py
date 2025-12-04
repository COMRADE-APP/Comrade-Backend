from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from Resources.models import Resource, ResourceVisibility
from Resources.serializers import ResourceSerializer, ResourceVisibilitySerializer
from Rooms.models import Room, DefaultRoom, DirectMessage, DirectMessageRoom, ForwadingLog
from Rooms.serializers import RoomSerializer, DefaultRoomSerializer, DirectMessageSerializer, DirectMessageRoomSerializer, ForwadingLogSerializer
from Announcements.models import AnnouncementsRequest, Announcements, Task, Text, CompletedTask, Pin, Reposts, Reply, QuestionResponse, Question, SubQuestion, Choice, FileResponse, TaskResponse, Reaction, Comment
from Announcements.serializers import AnnouncementsRequestSerializer, AnnouncementsSerializer, TaskSerializer, TextSerializer, CompletedTaskSerializer, PinSerializer, RepostsSerializer, ReplySerializer, QuestionResponseSerializer, QuestionSerializer, SubQuestionSerializer, ChoiceSerializer, FileResponseSerializer, TaskResponseSerializer, ReactionSerializer, CommentSerializer
from Organisation.models import Organisation, OrgBranch, Division, Department, Section, Team, Project, Centre, Committee, Board, Unit, Institute, Program
from Institution.models import Institution, InstBranch, VCOffice, Faculty, InstDepartment, AdminDep, Library, Hostel, Cafeteria, Programme, HR, Admissions, HealthServices, Security, StudentAffairs, SupportServices, Finance, Marketing, Legal, ICT, CareerOffice, Counselling, RegistrarOffice, Transport
from Rooms.permissions import IsModerator, IsAdmin
from Authentication.models import CustomUser as User, Student, StudentAdmin, Lecturer, InstAdmin, InstStaff, OrgAdmin, OrgStaff
from Authentication.serializers import CustomUserSerializer, StudentSerializer, StudentAdminSerializer, LecturerSerializer, InstAdminSerializer, InstStaffSerializer, OrgAdminSerializer, OrgStaffSerializer
from Events.serializers import EventSerializer
from Events.models import Event
from rest_framework.permissions import IsAuthenticated
from Resources.views import VISIBILITY_MAP



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
    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = RoomSerializer

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        room = self.get_object()
        user = request.user

        if user in room.members.all():
            return Response({"message": "user already exists in the room."}, status=status.HTTP_400_BAD_REQUEST)
        
        room.members.add(user)
        room.capacity_counter += 1
        room.save()
        return Response({"message": "Successfully joined the room."}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        room = self.get_object()
        user = request.user

        if user not in room.members.all():
            return Response({"message": "user is not a member of the room."}, status=status.HTTP_400_BAD_REQUEST)
        
        room.members.remove(user)
        room.capacity_counter -= 1
        room.save()
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
        # Allow create/update/delete for moderators/admins
        permission = IsModerator()
        if permission.has_permission(self, request):
            if request.method == 'POST':
                serializer = AnnouncementsSerializer(data=request.data)
                if serializer.is_valid():
                    serializer.save(room=room, created_by=request.user)
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            elif request.method in ['PUT', 'PATCH']:
                announcement_id = request.data.get('id')
                if not announcement_id:
                    return Response({"message": "Announcement id is required for update."}, status=status.HTTP_400_BAD_REQUEST)
                announcement = get_object_or_404(Announcements, id=announcement_id, room=room)
                serializer = AnnouncementsSerializer(announcement, data=request.data, partial=(request.method == 'PATCH'))
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            elif request.method == 'DELETE':
                announcement_id = request.data.get('id')
                if not announcement_id:
                    return Response({"message": "Announcement id is required for deletion."}, status=status.HTTP_400_BAD_REQUEST)
                announcement = get_object_or_404(Announcements, id=announcement_id, room=room)
                announcement.delete()
                return Response({"message": "Announcement deleted successfully."}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "You do not have permission to create or modify announcements."}, status=status.HTTP_403_FORBIDDEN)
        
    @action(detail=True, methods=['get', 'post', 'put', 'patch', 'delete'])
    def tasks(self, request, pk=None):
        room = self.get_object()
        if request.method == 'GET':
            tasks = Task.objects.filter(room=room)
            serializer = TaskSerializer(tasks, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        permission = IsModerator()
        if permission.has_permission(self, request):
            if request.method == 'POST':
                serializer = TaskSerializer(data=request.data)
                if serializer.is_valid():
                    serializer.save(room=room, created_by=request.user)
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            elif request.method in ['PUT', 'PATCH']:
                task_id = request.data.get('id')
                task = get_object_or_404(Task, id=task_id, room=room)
                serializer = TaskSerializer(task, data=request.data, partial=(request.method == 'PATCH'))
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            elif request.method == 'DELETE':
                task_id = request.data.get('id')
                task = get_object_or_404(Task, id=task_id, room=room)
                # Delete related questions, subquestions, and file responses
                Question.objects.filter(task=task).delete()
                SubQuestion.objects.filter(question__task=task).delete()
                FileResponse.objects.filter(task=task).delete()
                task.delete()
                return Response({"message": "Task and related content deleted successfully."}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "You do not have permission to create tasks."}, status=status.HTTP_403_FORBIDDEN)


    # @action(detail=False, methods=['post', 'get', 'put', 'patch', 'delete'])
    # def room_events(self, request):
    #     room_id = request.query_params.get('room_id')
    #     if not room_id:
    #         return Response({"message": "room_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
    #     room = get_object_or_404(Room, id=room_id)
        
    #     if request.method == 'GET':
    #         events = room.events
            
    #         # Filter by event type
    #         event_status = request.query_params.get('status')
    #         if event_status:
    #             events = events.filter(status=event_status)
            
    #         # Filter by created_by
    #         created_by = request.query_params.get('created_by')
    #         if created_by:
    #             events = events.filter(created_by__username=created_by)
            
    #         # Filter by date range
    #         start_date = request.query_params.get('start_date')
    #         end_date = request.query_params.get('end_date')
    #         if start_date and end_date:
    #             events = events.filter(created_at__range=[start_date, end_date])
            
    #         serializer = EventSerializer(events, many=True)
    #         return Response(serializer.data, status=status.HTTP_200_OK)
        
    #     permission = IsModerator()
    #     if permission.has_permission(self, request):
    #         if request.method == 'POST':
    #             serializer = EventSerializer(data=request.data)
    #             if serializer.is_valid():
    #                 serializer.save(room=room, created_by=request.user)
    #                 return Response(serializer.data, status=status.HTTP_201_CREATED)
    #             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
    #         elif request.method in ['PUT', 'PATCH']:
    #             event_id = request.data.get('id')
    #             event = Event.objects.get(id=event_id)
    #             serializer = EventSerializer(event, data=request.data, partial=(request.method == 'PATCH'))
    #             if serializer.is_valid():
    #                 serializer.save()
    #                 return Response(serializer.data, status=status.HTTP_200_OK)
    #             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
    #         elif request.method == 'DELETE':
    #             event_id = request.data.get('id')
    #             event = Event.objects.get(id=event_id)
    #             room.events.remove(event)
    #             return Response({"message": "Event deleted successfully."}, status=status.HTTP_200_OK)
        
    #     return Response({"message": "You do not have permission to manage room events."}, status=status.HTTP_403_FORBIDDEN)
    @action(detail=True, methods=['get'])
    def events(self, request, pk=None):
        room = self.get_object()
        events = room.events.all()
        # Apply filters...
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsModerator])
    def add_event(self, request, pk=None):
        room = self.get_object()
        serializer = EventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(room=room, created_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch', 'put'], permission_classes=[IsModerator])
    def update_event(self, request, pk=None):
        event = get_object_or_404(Event, pk=request.data.get('id'))
        serializer = EventSerializer(event, data=request.data, partial=(request.method == 'PATCH'))
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=['delete'], permission_classes=[IsModerator])
    def delete_event(self, request, pk=None):
        event = get_object_or_404(Event, pk=request.data.get('id'))
        event.delete()
        return Response({"message": "Event deleted successfully."})
    
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

    @action(detail=True, methods=['post'])
    def make_moderator(self, request, pk=None):
        room = self.get_object()
        if request.method == 'POST' and request.user.is_student_admin or request.user.is_inst_admin or request.user.is_org_admin or request.user.is_admin:
            user_id = request.data.get('user_id')
            user = get_object_or_404(User, id=user_id)
            room.moderators.add(user)
            return Response({"message": "User has been made a moderator."}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "You do not have permission to make moderators."}, status=status.HTTP_403_FORBIDDEN)
    
    @action(detail=True, methods=['post'])
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
        if int(room.capacity_counter) >= int(room.capacity_quota):
            return Response({'error': 'Sorry, the room is full at the moment.'}, status=status.HTTP_400_BAD_REQUEST)
            
        if request.method == 'POST' and request.user.is_student_admin or request.user.is_inst_admin or request.user.is_org_admin or request.user.is_admin:
            user_id = request.data.get('user_id')
            user = get_object_or_404(User, id=user_id)
            room.members.add(user)
            room.capacity_counter +=1
            room.save()
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
            room.capacity_counter -=1
            room.save()
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
        
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        room = Room.objects.get(pk=pk)
        # room = self.get_object()
        # room.admins.clear()
        # room.moderators.clear()
        # room.members.clear()
        # room.save()

    @action(detail=True, methods=['post'])
    def delete(self, request, pk=None):
        room = Room.objects.get(pk=pk)
        # room = self.get_object()

        room.admins.clear()
        room.moderators.clear()
        room.members.clear()
        room.save()

        return Response({'message':'Room has been deleted successfully. You have until 60 days to reverse the action. When 60 days are reached, the room will be deleted parmanently.'}, status=status.HTTP_200_OK)
    

class DefaultRoomViewSet(ModelViewSet):
    queryset = DefaultRoom.objects.all()
    # permission_classes = [permissions.IsAuthenticated]
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
        
    @action(detail=True, methods=['post'])
    def create_default_room_automatocally(self, request):
        inst_or_org_name = request.data.get('inst_or_org_name')
        unique_code = request.data.get('unique_code')
        reference_type = request.data.get('reference_type')

        if not (inst_or_org_name and reference_type and unique_code):
            return Response({'error': 'Could not fetch the institution/organisation name, reference code or type.'}, status=status.HTTP_400_BAD_REQUEST)

        
        try:
            room = DefaultRoom.objects.create(name=f'{inst_or_org_name} Room (Default)', inst_or_org_name=inst_or_org_name, created_by=request.user, reference_object_code=unique_code)

            data = {
                'room_id': room.id,
                'room_name': room.name,
                'ins_or_org_name': room.inst_or_org_name,
                'room_code': room.room_code,
                'reference_code': unique_code,
                'message': f'Default room for {inst_or_org_name} has been created successfully',
            }
            return Response(data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': f'The following error occured:\n{e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @action(detail=True, methods=['post', 'put', 'patch'])
    def add_members_automatically(self, request):
        member = request.user
        unique_code = request.data.get('unique_code')
        reference_type = request.data.get('reference_type')

        if not (reference_type and unique_code):
            return Response({'error': 'Could not fetch the institution/organisation name, reference code or type.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            room = get_object_or_404(DefaultRoom, reference_object_code=unique_code)
            room.members.add(member)
            room.save()

            data = {
                'room_id': room.id,
                'room_name': room.name,
                'ins_or_org_name': room.inst_or_org_name,
                'message': f'Member {member.first_name} has been added to their respective default room successfully.',
            }
            return Response(data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': f'The following error occured:\n{e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



        

class DirectMessageViewSet(ModelViewSet):
    queryset = DirectMessage.objects.all()
    serializer_class = DirectMessageSerializer
    # permission_classes = [IsAuthenticated]

class DirectMessageRoomViewSet(ModelViewSet):
    queryset = DirectMessageRoom.objects.all()
    serializer_class = DirectMessageRoomSerializer
    # permission_classes = [IsAuthenticated]

class ForwadingLogViewSet(ModelViewSet):
    queryset = ForwadingLog.objects.all()
    serializer_class = ForwadingLogSerializer
    # permission_classes = [IsAdmin]

    