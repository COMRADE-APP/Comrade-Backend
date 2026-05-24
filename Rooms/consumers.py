import json
import asyncio
from datetime import timedelta
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from .models import Room, RoomChat, DirectMessageRoom, DirectMessage, RoomTyping


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or isinstance(self.user, AnonymousUser):
            await self.close(code=4001)
            return

        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'

        is_member = await self.check_room_membership(self.user.id, self.room_id)
        if not is_member:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        self.heartbeat_task = asyncio.create_task(self._heartbeat())

    async def disconnect(self, close_code):
        if hasattr(self, 'heartbeat_task'):
            self.heartbeat_task.cancel()
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def _heartbeat(self):
        while True:
            await asyncio.sleep(30)
            try:
                await self.send(text_data=json.dumps({'type': 'ping'}))
            except Exception:
                break

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type', 'message')

        if msg_type == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_broadcast',
                    'user_id': self.user.id,
                    'first_name': self.user.first_name,
                    'avatar_url': await self.get_avatar_url(),
                }
            )
            return

        message = data.get('message', '').strip()
        if not message or len(message) > 5000:
            return

        saved_msg = await self.save_message(self.user.id, self.room_id, message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'user_id': str(self.user.id),
                'first_name': self.user.first_name,
                'msg_id': str(saved_msg.id),
                'created_at': saved_msg.created_at.isoformat(),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'user_id': event['user_id'],
            'first_name': event.get('first_name', ''),
            'msg_id': event.get('msg_id', ''),
            'created_at': event.get('created_at', ''),
        }))

    async def typing_broadcast(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'first_name': event.get('first_name', ''),
            'avatar_url': event.get('avatar_url', ''),
        }))

    @database_sync_to_async
    def get_avatar_url(self):
        if hasattr(self.user, 'user_profile') and self.user.user_profile.avatar:
            return self.user.user_profile.avatar.url
        return ''

    @database_sync_to_async
    def check_room_membership(self, user_id, room_id):
        try:
            room = Room.objects.get(id=room_id)
            return (
                room.members.filter(id=user_id).exists() or
                room.admins.filter(id=user_id).exists() or
                room.moderators.filter(id=user_id).exists()
            )
        except Room.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, user_id, room_id, message):
        from Authentication.models import CustomUser
        user = CustomUser.objects.get(id=user_id)
        room = Room.objects.get(id=room_id)
        return RoomChat.objects.create(
            sender=user.profile, room=room, content=message
        )


class DMChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or isinstance(self.user, AnonymousUser):
            await self.close(code=4001)
            return

        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'dm_{self.conversation_id}'

        is_participant = await self.check_participant(self.user.id, self.conversation_id)
        if not is_participant:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        self.heartbeat_task = asyncio.create_task(self._heartbeat())

    async def disconnect(self, close_code):
        if hasattr(self, 'heartbeat_task'):
            self.heartbeat_task.cancel()
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def _heartbeat(self):
        while True:
            await asyncio.sleep(30)
            try:
                await self.send(text_data=json.dumps({'type': 'ping'}))
            except Exception:
                break

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type', 'message')

        if msg_type == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_broadcast',
                    'user_id': self.user.id,
                    'first_name': self.user.first_name,
                    'avatar_url': await self.get_avatar_url(),
                }
            )
            return

        message = data.get('message', '').strip()
        if not message or len(message) > 5000:
            return

        saved_msg = await self.save_dm_message(self.user.id, self.conversation_id, message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'dm_message',
                'message': message,
                'sender_id': str(self.user.id),
                'sender_name': f'{self.user.first_name} {self.user.last_name}'.strip(),
                'msg_id': str(saved_msg.id),
                'time_stamp': saved_msg.time_stamp.isoformat(),
            }
        )

    async def dm_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'dm_message',
            'message': event['message'],
            'sender_id': event['sender_id'],
            'sender_name': event.get('sender_name', ''),
            'msg_id': event.get('msg_id', ''),
            'time_stamp': event.get('time_stamp', ''),
        }))

    async def typing_broadcast(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'first_name': event.get('first_name', ''),
            'avatar_url': event.get('avatar_url', ''),
        }))

    @database_sync_to_async
    def get_avatar_url(self):
        if hasattr(self.user, 'user_profile') and self.user.user_profile.avatar:
            return self.user.user_profile.avatar.url
        return ''

    @database_sync_to_async
    def check_participant(self, user_id, conversation_id):
        try:
            room = DirectMessageRoom.objects.get(id=conversation_id)
            return room.participants.filter(id=user_id).exists()
        except DirectMessageRoom.DoesNotExist:
            return False

    @database_sync_to_async
    def save_dm_message(self, user_id, conversation_id, message):
        from Authentication.models import CustomUser
        sender = CustomUser.objects.get(id=user_id)
        room = DirectMessageRoom.objects.get(id=conversation_id)
        receiver = room.participants.exclude(id=user_id).first()
        return DirectMessage.objects.create(
            sender=sender,
            receiver=receiver,
            content=message,
            dm_room=room,
            status='sent',
        )
