import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import SupportChatThread


class SupportChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        try:
            self.thread_id = int(self.scope["url_route"]["kwargs"]["thread_id"])
        except (TypeError, ValueError):
            await self.close(code=4400)
            return

        if not await self._can_connect(user.id, self.thread_id):
            await self.close(code=4403)
            return

        self.group_name = f"support_chat_{self.thread_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # Outgoing messages are sent via HTTP form post + group broadcast.
        return

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["message"], ensure_ascii=False))

    @database_sync_to_async
    def _can_connect(self, user_id: int, thread_id: int) -> bool:
        return SupportChatThread.objects.filter(id=thread_id, user_id=user_id).exists()
