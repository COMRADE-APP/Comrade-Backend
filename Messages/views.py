from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q, Max, F
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import Conversation, ConversationParticipant, Message, MessageRead, UserMessagingSettings
from .serializers import (
    ConversationSerializer, ConversationDetailSerializer, MessageSerializer,
    UserMessagingSettingsSerializer, StartConversationSerializer, SendMessageSerializer
)
from Authentication.models import CustomUser
from Opinions.models import Follow


def get_relationship(user1, user2):
    """
    Determine the follow relationship between two users
    Returns: 'mutual', 'following', 'follower', 'none'
    """
    user1_follows_user2 = Follow.objects.filter(follower=user1, following=user2).exists()
    user2_follows_user1 = Follow.objects.filter(follower=user2, following=user1).exists()
    
    if user1_follows_user2 and user2_follows_user1:
        return 'mutual'
    elif user1_follows_user2:
        return 'following'
    elif user2_follows_user1:
        return 'follower'
    return 'none'


def can_message_user(sender, receiver):
    """
    Check if sender can message receiver based on receiver's settings
    Returns: (can_message, is_request)
    """
    settings, _ = UserMessagingSettings.objects.get_or_create(user=receiver)
    relationship = get_relationship(sender, receiver)
    
    if settings.allow_messages_from == 'nobody':
        return False, False
    elif settings.allow_messages_from == 'mutual':
        if relationship == 'mutual':
            return True, False
        return False, False
    elif settings.allow_messages_from == 'following':
        if relationship in ['mutual', 'follower']:  # receiver follows sender
            return True, False
        return False, False
    elif settings.allow_messages_from == 'followers':
        if relationship in ['mutual', 'following']:  # sender follows receiver
            if relationship == 'mutual':
                return True, False
            return True, True  # Message request
        return False, False
    else:  # everyone
        if relationship == 'mutual':
            return True, False
        return True, True  # Message request for non-mutuals


def get_or_create_conversation(user1, user2):
    """
    Get existing DM conversation or create new one between two users.
    Handles message request logic.
    """
    # Check for existing conversation
    conversation = Conversation.objects.filter(
        conversation_type='dm',
        participants=user1
    ).filter(
        participants=user2
    ).first()
    
    if conversation:
        return conversation, False
    
    # Create new conversation
    conversation = Conversation.objects.create(conversation_type='dm')
    conversation.participants.add(user1, user2)
    
    # Determine if this is a request
    can_message, is_request = can_message_user(user1, user2)
    
    # Create participant details
    ConversationParticipant.objects.create(
        conversation=conversation,
        user=user1,
        is_request=False,  # Sender never sees it as request
        request_accepted=True
    )
    ConversationParticipant.objects.create(
        conversation=conversation,
        user=user2,
        is_request=is_request,
        request_accepted=not is_request
    )
    
    return conversation, True


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversations
    """
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Conversation.objects.filter(
            participants=user,
            participant_details__user=user,
            participant_details__is_archived=False
        ).distinct()
        
        # Filter by type
        conv_type = self.request.query_params.get('type')
        if conv_type == 'requests':
            queryset = queryset.filter(
                participant_details__user=user,
                participant_details__is_request=True,
                participant_details__request_accepted=False
            )
        elif conv_type == 'dm':
            queryset = queryset.filter(conversation_type='dm')
        
        return queryset.order_by('-updated_at')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ConversationDetailSerializer
        return ConversationSerializer
    
    @action(detail=False, methods=['post'])
    def start(self, request):
        """Start a new conversation with a user"""
        serializer = StartConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_id = serializer.validated_data['user_id']
        initial_message = serializer.validated_data.get('message', '')
        
        if user_id == request.user.id:
            return Response(
                {'error': 'Cannot start conversation with yourself'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        target_user = get_object_or_404(CustomUser, id=user_id)
        
        # Check if messaging is allowed
        can_message, is_request = can_message_user(request.user, target_user)
        if not can_message:
            return Response(
                {'error': 'You cannot message this user'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        conversation, created = get_or_create_conversation(request.user, target_user)
        
        # Send initial message if provided
        if initial_message:
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=initial_message,
                message_type='text'
            )
            conversation.updated_at = timezone.now()
            conversation.save()
        
        return Response({
            'conversation': ConversationSerializer(conversation, context={'request': request}).data,
            'created': created,
            'is_request': is_request
        })
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send a message in a conversation"""
        conversation = self.get_object()
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        content = serializer.validated_data.get('content', '')
        message_type = serializer.validated_data.get('message_type', 'text')
        reply_to_id = serializer.validated_data.get('reply_to')
        
        reply_to = None
        if reply_to_id:
            reply_to = Message.objects.filter(id=reply_to_id, conversation=conversation).first()
        
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content,
            message_type=message_type,
            reply_to=reply_to
        )
        
        # Handle media upload
        if 'media' in request.FILES:
            message.media = request.FILES['media']
            message.save()
        
        # Update conversation timestamp
        conversation.updated_at = timezone.now()
        conversation.save()
        
        # Update sender's last_read
        participant = ConversationParticipant.objects.filter(
            conversation=conversation,
            user=request.user
        ).first()
        if participant:
            participant.last_read_at = timezone.now()
            participant.save()
        
        return Response(
            MessageSerializer(message, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark all messages in conversation as read"""
        conversation = self.get_object()
        participant = ConversationParticipant.objects.filter(
            conversation=conversation,
            user=request.user
        ).first()
        
        if participant:
            participant.last_read_at = timezone.now()
            participant.save()
        
        return Response({'status': 'marked_read'})
    
    @action(detail=True, methods=['post'])
    def accept_request(self, request, pk=None):
        """Accept a message request"""
        conversation = self.get_object()
        participant = ConversationParticipant.objects.filter(
            conversation=conversation,
            user=request.user,
            is_request=True
        ).first()
        
        if participant:
            participant.is_request = False
            participant.request_accepted = True
            participant.save()
            return Response({'status': 'accepted'})
        
        return Response(
            {'error': 'No pending request'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['post'])
    def decline_request(self, request, pk=None):
        """Decline/delete a message request"""
        conversation = self.get_object()
        participant = ConversationParticipant.objects.filter(
            conversation=conversation,
            user=request.user,
            is_request=True
        ).first()
        
        if participant:
            participant.is_archived = True
            participant.save()
            return Response({'status': 'declined'})
        
        return Response(
            {'error': 'No pending request'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['post'])
    def toggle_mute(self, request, pk=None):
        """Toggle mute for conversation"""
        conversation = self.get_object()
        participant = ConversationParticipant.objects.filter(
            conversation=conversation,
            user=request.user
        ).first()
        
        if participant:
            participant.is_muted = not participant.is_muted
            participant.save()
            return Response({'is_muted': participant.is_muted})
        
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def toggle_pin(self, request, pk=None):
        """Toggle pin for conversation"""
        conversation = self.get_object()
        participant = ConversationParticipant.objects.filter(
            conversation=conversation,
            user=request.user
        ).first()
        
        if participant:
            participant.is_pinned = not participant.is_pinned
            participant.save()
            return Response({'is_pinned': participant.is_pinned})
        
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive conversation"""
        conversation = self.get_object()
        participant = ConversationParticipant.objects.filter(
            conversation=conversation,
            user=request.user
        ).first()
        
        if participant:
            participant.is_archived = True
            participant.save()
            return Response({'status': 'archived'})
        
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'])
    def requests(self, request):
        """Get message requests"""
        conversations = Conversation.objects.filter(
            participants=request.user,
            participant_details__user=request.user,
            participant_details__is_request=True,
            participant_details__request_accepted=False
        ).distinct().order_by('-updated_at')
        
        serializer = ConversationSerializer(conversations, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def circles(self, request):
        """
        Get all mutual followers (circles) with existing or potential conversations
        Creates empty conversations for mutual followers who haven't chatted yet
        """
        user = request.user
        
        # Get all mutual followers
        following_ids = Follow.objects.filter(follower=user).values_list('following_id', flat=True)
        followers_ids = Follow.objects.filter(following=user).values_list('follower_id', flat=True)
        mutual_ids = set(following_ids) & set(followers_ids)
        
        circles = []
        for mutual_id in mutual_ids:
            mutual_user = CustomUser.objects.get(id=mutual_id)
            conversation, created = get_or_create_conversation(user, mutual_user)
            
            circles.append({
                'user': {
                    'id': mutual_user.id,
                    'first_name': mutual_user.first_name,
                    'last_name': mutual_user.last_name,
                    'full_name': f"{mutual_user.first_name or ''} {mutual_user.last_name or ''}".strip(),
                    'avatar_url': None  # Add avatar logic here
                },
                'conversation_id': conversation.id,
                'has_messages': conversation.messages.exists(),
                'last_message': conversation.get_last_message().content[:30] if conversation.get_last_message() else None
            })
        
        return Response(circles)


class MessagingSettingsView(APIView):
    """
    Get and update messaging settings
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        settings, _ = UserMessagingSettings.objects.get_or_create(user=request.user)
        serializer = UserMessagingSettingsSerializer(settings)
        return Response(serializer.data)
    
    def patch(self, request):
        settings, _ = UserMessagingSettings.objects.get_or_create(user=request.user)
        serializer = UserMessagingSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
