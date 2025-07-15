from django.urls import re_path

def get_websocket_urlpatterns():
    from . import consumers
    return [
        re_path(r'^api/ws/categorias/$', consumers.CategoriasConsumer.as_asgi()),
        re_path(r'^api/ws/notificaciones/$', consumers.NotificacionesConsumer.as_asgi()),
        re_path(r'^api/ws/productos-destacados/$', consumers.ProductosDestacadosConsumer.as_asgi()),
    ]

websocket_urlpatterns = get_websocket_urlpatterns()