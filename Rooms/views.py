from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from Resources.models import Resource, ResourceVisibility 
from Resources.serializers import ResourceSerializer, ResourceVisibilitySerializer
from Rooms.models import Room, DefaultRoom, DirectMessage, DirectMessageRoom, ForwadingLog, RoomSettings, RoomChat, RoomChatFile
from Rooms.serializers import (
    RoomSerializer, RoomListSerializer, RoomRecommendationSerializer,
    DefaultRoomSerializer, DirectMessageSerializer, DirectMessageCreateSerializer,
    DirectMessageRoomSerializer, DirectMessageRoomListSerializer, ForwadingLogSerializer,
    RoomChatSerializer, RoomChatCreateSerializer, RoomSettingsSerializer, 
    RoomDetailSerializer, MemberDetailSerializer, RoomChatFileSerializer
)
from Opinions.models import Follow
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
from datetime import datetime



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
    
    def get_serializer_class(self):
        if self.action == 'list':
            return RoomListSerializer
        if self.action == 'recommendations':
            return RoomRecommendationSerializer
        return RoomSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def get_queryset(self):
        """Filter rooms based on query parameters"""
        queryset = Room.objects.filter(operation_state='active')
        
        # Filter by name search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        # Filter by institution
        institution = self.request.query_params.get('institution')
        if institution:
            queryset = queryset.filter(institutions__id=institution)
        
        return queryset.order_by('-created_on')
    
    def perform_create(self, serializer):
        room = serializer.save(created_by=self.request.user)
        # Add creator as admin and member
        room.admins.add(self.request.user)
        room.members.add(self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_rooms(self, request):
        """Get rooms the user is a member of"""
        rooms = Room.objects.filter(
            members=request.user,
            operation_state='active'
        ).order_by('-created_on')
        serializer = RoomListSerializer(rooms, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        """Get recommended rooms for the user based on institution and activity"""
        user = request.user
        
        # Get rooms user is NOT already a member of
        user_room_ids = Room.objects.filter(members=user).values_list('id', flat=True)
        
        # Start with active rooms
        queryset = Room.objects.filter(
            operation_state='active'
        ).exclude(id__in=user_room_ids)
        
        # Try to find institution-based recommendations
        institution_rooms = queryset.none()
        if hasattr(user, 'student'):
            try:
                student = user.student
                # Find rooms associated with same institution
                institution_rooms = queryset.filter(
                    institutions__name__icontains=student.institution
                )
                for room in institution_rooms:
                    room.match_reason = 'From your institution'
            except:
                pass
        
        # Get popular rooms (by member count)
        popular_rooms = queryset.annotate(
            member_count_val=Count('members')
        ).order_by('-member_count_val')[:10]
        for room in popular_rooms:
            if not hasattr(room, 'match_reason'):
                room.match_reason = 'Popular room'
        
        # Combine recommendations (institution first, then popular)
        recommendations = list(institution_rooms[:5]) + list(popular_rooms[:5])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for room in recommendations:
            if room.id not in seen:
                seen.add(room.id)
                unique_recommendations.append(room)
        
        serializer = RoomRecommendationSerializer(
            unique_recommendations[:10], 
            many=True, 
            context={'request': request}
        )
        return Response(serializer.data)
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
    
    # ==================== CHAT ENDPOINTS ====================
    
    @action(detail=True, methods=['get', 'post'])
    def chats(self, request, pk=None):
        """Get or send room chat messages"""
        room = self.get_object()
        
        # Check if user is member
        if request.user not in room.members.all():
            return Response({'error': 'You are not a member of this room'}, 
                            status=status.HTTP_403_FORBIDDEN)
        
        if request.method == 'GET':
            # Get chats with optional filters
            chats = RoomChat.objects.filter(room=room, is_deleted=False).select_related('sender')
            
            # Filter by message type
            msg_type = request.query_params.get('type')
            if msg_type:
                chats = chats.filter(message_type=msg_type)
            
            # Pagination
            page = self.paginate_queryset(chats)
            if page is not None:
                serializer = RoomChatSerializer(page, many=True, context={'request': request})
                return self.get_paginated_response(serializer.data)
            
            serializer = RoomChatSerializer(chats, many=True, context={'request': request})
            return Response(serializer.data)
        
        elif request.method == 'POST':
            # Check chat permission
            settings, created = RoomSettings.objects.get_or_create(room=room)
            
            if not settings.chat_enabled:
                return Response({'error': 'Chat is disabled in this room'}, 
                                status=status.HTTP_403_FORBIDDEN)
            
            permission = settings.chat_permission
            if permission == 'admins_only' and request.user not in room.admins.all():
                return Response({'error': 'Only admins can send messages'}, 
                                status=status.HTTP_403_FORBIDDEN)
            if permission == 'admins_moderators':
                if request.user not in room.admins.all() and request.user not in room.moderators.all():
                    return Response({'error': 'Only admins and moderators can send messages'}, 
                                    status=status.HTTP_403_FORBIDDEN)
            
            # Create chat message
            serializer = RoomChatCreateSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                chat = serializer.save(room=room, sender=request.user, status='sent')
                
                # Handle file uploads
                files = request.FILES.getlist('files')
                for file in files:
                    file_type = 'document'
                    if file.content_type.startswith('image/'):
                        file_type = 'image'
                    elif file.content_type.startswith('video/'):
                        file_type = 'video'
                    elif file.content_type.startswith('audio/'):
                        file_type = 'audio'
                    
                    chat_file = RoomChatFile.objects.create(
                        file=file,
                        file_name=file.name,
                        file_type=file_type,
                        file_size=file.size,
                        uploaded_by=request.user
                    )
                    chat.files.add(chat_file)
                
                # Update message type if files attached
                if files:
                    chat.message_type = 'file'
                    chat.save()
                
                return Response(RoomChatSerializer(chat, context={'request': request}).data, 
                                status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], url_path='chats/(?P<chat_id>[^/.]+)/forward')
    def forward_chat(self, request, pk=None, chat_id=None):
        """Forward a chat message to another room"""
        room = self.get_object()
        chat = get_object_or_404(RoomChat, id=chat_id, room=room)
        target_room_id = request.data.get('target_room')
        
        if not target_room_id:
            return Response({'error': 'target_room is required'}, 
                            status=status.HTTP_400_BAD_REQUEST)
        
        target_room = get_object_or_404(Room, id=target_room_id)
        
        # Check if user is member of target room
        if request.user not in target_room.members.all():
            return Response({'error': 'You are not a member of the target room'}, 
                            status=status.HTTP_403_FORBIDDEN)
        
        # Check if forwarding is allowed
        settings = getattr(room, 'settings', None)
        if settings and not settings.allow_message_forwarding:
            return Response({'error': 'Message forwarding is disabled in this room'}, 
                            status=status.HTTP_403_FORBIDDEN)
        
        # Create forwarded message
        new_chat = RoomChat.objects.create(
            room=target_room,
            sender=request.user,
            content=chat.content,
            message_type=chat.message_type,
            is_forwarded=True,
            forwarded_from_room=room if settings and settings.show_forward_source else None,
            forwarded_from_user=request.user,
            original_chat=chat,
            status='sent'
        )
        
        # Copy files
        for file in chat.files.all():
            new_chat.files.add(file)
        
        return Response(RoomChatSerializer(new_chat, context={'request': request}).data, 
                        status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], url_path='chats/(?P<chat_id>[^/.]+)/read')
    def mark_chat_read(self, request, pk=None, chat_id=None):
        """Mark a chat message as read"""
        room = self.get_object()
        chat = get_object_or_404(RoomChat, id=chat_id, room=room)
        
        if request.user not in room.members.all():
            return Response({'error': 'You are not a member of this room'}, 
                            status=status.HTTP_403_FORBIDDEN)
        
        chat.read_by.add(request.user)
        
        # Update status if all members have read
        if chat.read_by.count() >= room.members.count() - 1:  # Exclude sender
            chat.status = 'read'
            chat.save()
        
        return Response({'message': 'Message marked as read'})
    
    @action(detail=True, methods=['delete'], url_path='chats/(?P<chat_id>[^/.]+)')
    def delete_chat(self, request, pk=None, chat_id=None):
        """Delete a chat message (soft delete)"""
        room = self.get_object()
        chat = get_object_or_404(RoomChat, id=chat_id, room=room)
        
        # Only sender or admins can delete
        if chat.sender != request.user and request.user not in room.admins.all():
            return Response({'error': 'You can only delete your own messages'}, 
                            status=status.HTTP_403_FORBIDDEN)
        
        chat.is_deleted = True
        chat.deleted_at = datetime.now()
        chat.save()
        
        return Response({'message': 'Message deleted'})
    
    # ==================== SETTINGS ENDPOINTS ====================
    
    @action(detail=True, methods=['get', 'put', 'patch'])
    def room_settings(self, request, pk=None):
        """Get or update room settings"""
        room = self.get_object()
        
        # Only admins can update settings
        if request.method in ['PUT', 'PATCH']:
            if request.user not in room.admins.all():
                return Response({'error': 'Only admins can update settings'}, 
                                status=status.HTTP_403_FORBIDDEN)
        
        settings, created = RoomSettings.objects.get_or_create(room=room)
        
        if request.method == 'GET':
            serializer = RoomSettingsSerializer(settings)
            return Response(serializer.data)
        
        serializer = RoomSettingsSerializer(settings, data=request.data, 
                                             partial=(request.method == 'PATCH'))
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # ==================== MEMBER DETAIL ENDPOINTS ====================
    
    @action(detail=True, methods=['get'])
    def members_detail(self, request, pk=None):
        """Get detailed member list with roles and follow status"""
        room = self.get_object()
        members = room.members.all()
        
        result = []
        for member in members:
            role = 'member'
            if member in room.admins.all():
                role = 'admin'
            elif member in room.moderators.all():
                role = 'moderator'
            
            # Check if current user is following this member
            is_following = Follow.objects.filter(
                follower=request.user, following=member
            ).exists() if request.user.is_authenticated else False
            
            avatar_url = None
            if hasattr(member, 'user_profile') and member.user_profile and member.user_profile.avatar:
                avatar_url = request.build_absolute_uri(member.user_profile.avatar.url)
            
            result.append({
                'id': member.id,
                'email': member.email,
                'first_name': member.first_name,
                'last_name': member.last_name,
                'full_name': f"{member.first_name} {member.last_name}",
                'avatar_url': avatar_url,
                'role': role,
                'is_following': is_following,
                'user_type': member.user_type,
            })
        
        return Response(result)
    
    @action(detail=True, methods=['post'], url_path='members/(?P<user_id>[^/.]+)/follow')
    def follow_member(self, request, pk=None, user_id=None):
        """Follow/unfollow a room member"""
        room = self.get_object()
        target_user = get_object_or_404(User, id=user_id)
        
        if target_user not in room.members.all():
            return Response({'error': 'User is not a member of this room'}, 
                            status=status.HTTP_400_BAD_REQUEST)
        
        if target_user == request.user:
            return Response({'error': 'Cannot follow yourself'}, 
                            status=status.HTTP_400_BAD_REQUEST)
        
        follow, created = Follow.objects.get_or_create(
            follower=request.user, following=target_user
        )
        
        if not created:
            follow.delete()
            return Response({'message': 'Unfollowed user', 'is_following': False})
        
        return Response({'message': 'Now following user', 'is_following': True})
    

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
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter messages for the current user"""
        user = self.request.user
        dm_room_id = self.request.query_params.get('dm_room')
        
        queryset = DirectMessage.objects.filter(
            Q(sender=user) | Q(receiver=user)
        ).order_by('-time_stamp')
        
        if dm_room_id:
            queryset = queryset.filter(dm_room_id=dm_room_id)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return DirectMessageCreateSerializer
        return DirectMessageSerializer
    
    def perform_create(self, serializer):
        serializer.save(sender=self.request.user, status='sent')
    
    @action(detail=False, methods=['post'])
    def send(self, request):
        """Send a new direct message"""
        receiver_id = request.data.get('receiver')
        content = request.data.get('content')
        dm_room_id = request.data.get('dm_room')
        file = request.data.get('file')
        
        if not receiver_id or not content:
            return Response(
                {'error': 'receiver and content are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        receiver = get_object_or_404(User, id=receiver_id)
        
        # Get or create DM room
        if not dm_room_id:
            dm_room = DirectMessageRoom.objects.filter(
                participants=request.user
            ).filter(
                participants=receiver
            ).first()
            
            if not dm_room:
                dm_room = DirectMessageRoom.objects.create()
                dm_room.participants.add(request.user, receiver)
        else:
            dm_room = get_object_or_404(DirectMessageRoom, id=dm_room_id)
        
        message = DirectMessage.objects.create(
            sender=request.user,
            receiver=receiver,
            content=content,
            dm_room=dm_room,
            file=file,
            status='sent',
            message_type='text' if not file else 'file'
        )
        
        serializer = DirectMessageSerializer(message, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a message as read"""
        message = self.get_object()
        if message.receiver == request.user:
            message.is_read = True
            message.status = 'read'
            message.read_on = datetime.now()
            message.save()
            return Response({'message': 'Message marked as read'})
        return Response(
            {'error': 'You can only mark messages sent to you as read'},
            status=status.HTTP_403_FORBIDDEN
        )


class DirectMessageRoomViewSet(ModelViewSet):
    queryset = DirectMessageRoom.objects.all()
    serializer_class = DirectMessageRoomSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get only DM rooms the user is part of"""
        return DirectMessageRoom.objects.filter(
            participants=self.request.user
        ).order_by('-created_on')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return DirectMessageRoomListSerializer
        return DirectMessageRoomSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    @action(detail=False, methods=['post'])
    def get_or_create(self, request):
        """Get existing DM room with user or create new one"""
        other_user_id = request.data.get('user_id')
        
        if not other_user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        other_user = get_object_or_404(User, id=other_user_id)
        
        # Check if DM room already exists
        dm_room = DirectMessageRoom.objects.filter(
            participants=request.user
        ).filter(
            participants=other_user
        ).first()
        
        if not dm_room:
            dm_room = DirectMessageRoom.objects.create()
            dm_room.participants.add(request.user, other_user)
        
        serializer = DirectMessageRoomSerializer(dm_room, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Get all messages for a DM room"""
        dm_room = self.get_object()
        messages = dm_room.messages.all().order_by('time_stamp')
        
        # Paginate
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = DirectMessageSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = DirectMessageSerializer(messages, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_all_read(self, request, pk=None):
        """Mark all messages in room as read"""
        dm_room = self.get_object()
        updated = dm_room.messages.filter(
            receiver=request.user,
            is_read=False
        ).update(is_read=True, status='read')
        
        return Response({'messages_marked_read': updated})


class ForwadingLogViewSet(ModelViewSet):
    queryset = ForwadingLog.objects.all()
    serializer_class = ForwadingLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ForwadingLog.objects.filter(user=self.request.user)
