import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or isinstance(self.user, AnonymousUser):
            await self.close(code=4001)
            return

        requested_user_id = self.scope['url_route']['kwargs']['user_id']
        if str(self.user.id) != requested_user_id:
            await self.close(code=4003)
            return

        self.group_name = f'notify_{self.user.id}'

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def send_notification(self, event):
        payload = event['payload']
        payload['unread_count'] = await self._get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'payload': payload
        }))

    @database_sync_to_async
    def _get_unread_count(self):
        return self.user.notifications.filter(is_read=False).count()
