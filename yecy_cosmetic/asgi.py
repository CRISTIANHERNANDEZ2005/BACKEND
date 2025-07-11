
import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import tienda.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "yecy_cosmetic.settings")

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            tienda.routing.websocket_urlpatterns
        )
    ),
})
