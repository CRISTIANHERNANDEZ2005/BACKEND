from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/notificaciones/(?P<rol>cliente|admin)/(?P<usuario_id>\d+)/$', consumers.NotificacionConsumer.as_asgi()),
]
