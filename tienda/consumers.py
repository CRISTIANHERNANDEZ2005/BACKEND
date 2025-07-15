import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Categoria, Subcategoria, Producto
from .serializers import CategoriaSerializer, SubcategoriaSerializer, ProductoSerializer
from django.core.cache import cache
import asyncio

class CategoriasConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Conectado al servidor de categorías'
        }))

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'get_categorias':
                categorias = await self.get_categorias()
                await self.send(text_data=json.dumps({
                    'type': 'categorias_data',
                    'data': categorias
                }))

            elif message_type == 'get_subcategorias':
                categoria_id = data.get('categoria_id')
                if categoria_id:
                    subcategorias = await self.get_subcategorias(categoria_id)
                    await self.send(text_data=json.dumps({
                        'type': 'subcategorias_data',
                        'categoria_id': categoria_id,
                        'data': subcategorias
                    }))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Formato JSON inválido'
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    @database_sync_to_async
    def get_categorias(self):
        """Obtener categorías con cache para optimizar rendimiento"""
        cache_key = 'categorias_publicas'
        categorias = cache.get(cache_key)
        
        if not categorias:
            categorias = Categoria.objects.filter(activo=True).prefetch_related('subcategoria_set')
            serializer = CategoriaSerializer(categorias, many=True)
            categorias = serializer.data
            # Cache por 5 minutos
            cache.set(cache_key, categorias, 300)
        
        return categorias

    @database_sync_to_async
    def get_subcategorias(self, categoria_id):
        """Obtener subcategorías con cache para optimizar rendimiento"""
        cache_key = f'subcategorias_categoria_{categoria_id}'
        subcategorias = cache.get(cache_key)
        
        if not subcategorias:
            try:
                subcategorias = Subcategoria.objects.filter(
                    categoria_id=categoria_id,
                    activo=True
                )
                serializer = SubcategoriaSerializer(subcategorias, many=True)
                subcategorias = serializer.data
                # Cache por 5 minutos
                cache.set(cache_key, subcategorias, 300)
            except Categoria.DoesNotExist:
                subcategorias = []
        
        return subcategorias

class NotificacionesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Conectado al servidor de notificaciones'
        }))

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'subscribe_notifications':
                # Aquí puedes implementar suscripción a notificaciones específicas
                await self.send(text_data=json.dumps({
                    'type': 'subscription_confirmed',
                    'message': 'Suscripción confirmada'
                }))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Formato JSON inválido'
            }))

    async def notification_message(self, event):
        """Enviar notificación a todos los clientes conectados"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'message': event['message'],
            'data': event.get('data', {})
        }))

class ProductosDestacadosConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Conectado al servidor de productos destacados'
        }))

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'get_productos_destacados':
                productos = await self.get_productos_destacados()
                await self.send(text_data=json.dumps({
                    'type': 'productos_destacados_data',
                    'data': productos
                }))
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Formato JSON inválido'
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    @database_sync_to_async
    def get_productos_destacados(self):
        """Obtener productos destacados con cache para optimizar rendimiento"""
        cache_key = 'productos_destacados_publicos'
        productos = cache.get(cache_key)
        if not productos:
            productos_qs = Producto.objects.filter(activo=True, destacado=True, stock__gt=0).prefetch_related('imagenes')
            serializer = ProductoSerializer(productos_qs, many=True)
            productos = serializer.data
            # Cache por 5 minutos
            cache.set(cache_key, productos, 300)
        return productos
