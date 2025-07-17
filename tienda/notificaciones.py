from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Notificacion, Usuario
from django.utils import timezone

def notificar_usuario(usuario, mensaje, tipo='info'):
    """
    Notifica a un usuario (o a todos los admins si usuario=None) solo de forma persistente (base de datos).
    """
    if usuario is None:
        # Notificar a todos los admins
        admins = Usuario.objects.filter(es_admin=True, esta_activo=True)
        for admin in admins:
            Notificacion.objects.create(usuario=admin, tipo=tipo, mensaje=mensaje, creada=timezone.now())
    else:
        Notificacion.objects.create(usuario=usuario, tipo=tipo, mensaje=mensaje, creada=timezone.now())
