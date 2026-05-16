import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # ── Authentication Gate ──────────────────────────────────────────
        self.user = self.scope.get("user")
        if not self.user or isinstance(self.user, AnonymousUser):
            await self.close(code=4001)
            return

        # Users can only subscribe to their OWN notification channel
        requested_user_id = self.scope['url_route']['kwargs']['user_id']
        if str(self.user.id) != requested_user_id:
            await self.close(code=4003)  # Cannot subscribe to other users' notifications
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
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'payload': payload
        }))
