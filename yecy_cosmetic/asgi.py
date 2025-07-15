
import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

def get_websocket_urlpatterns():
    from tienda.routing import websocket_urlpatterns
    return websocket_urlpatterns

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "yecy_cosmetic.settings")

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            get_websocket_urlpatterns()
        )
    ),
})
