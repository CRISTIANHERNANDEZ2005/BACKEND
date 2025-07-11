import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()

class NotificacionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.rol = self.scope['url_route']['kwargs']['rol']
        self.usuario_id = self.scope['url_route']['kwargs']['usuario_id']
        self.group_name = f"notificaciones_{self.rol}_{self.usuario_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        # Este método puede usarse si quieres recibir mensajes del cliente (opcional)
        pass

    async def enviar_notificacion(self, event):
        await self.send(text_data=json.dumps(event['contenido']))
