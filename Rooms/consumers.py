import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import Room, RoomChat

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # ── Authentication Gate ──────────────────────────────────────────
        self.user = self.scope.get("user")
        if not self.user or isinstance(self.user, AnonymousUser):
            await self.close(code=4001)  # Unauthorized
            return

        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'

        # ── Membership Check ─────────────────────────────────────────────
        is_member = await self.check_room_membership(self.user.id, self.room_id)
        if not is_member:
            await self.close(code=4003)  # Forbidden
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message', '').strip()

        # Validate message content
        if not message or len(message) > 5000:
            return

        # Use authenticated user — NEVER trust client-supplied user_id
        saved_msg = await self.save_message(self.user.id, self.room_id, message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'user_id': str(self.user.id),
                'msg_id': str(saved_msg.id)
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'user_id': event['user_id'],
            'msg_id': event.get('msg_id', '')
        }))

    @database_sync_to_async
    def check_room_membership(self, user_id, room_id):
        """Verify the user is a member, admin, or moderator of the room."""
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
