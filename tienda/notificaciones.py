from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Notificacion, Usuario
from django.utils import timezone

def notificar_usuario(usuario, mensaje, tipo='info'):
    """
    Notifica a un usuario (o a todos los admins si usuario=None) tanto por WebSocket como persistente.
    """
    channel_layer = get_channel_layer()
    if usuario is None:
        # Notificar a todos los admins
        admins = Usuario.objects.filter(es_admin=True, esta_activo=True)
        for admin in admins:
            Notificacion.objects.create(usuario=admin, tipo=tipo, mensaje=mensaje, creada=timezone.now())
            group_name = f"notificaciones_admin_{admin.id}"
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    'type': 'enviar_notificacion',
                    'contenido': {'mensaje': mensaje, 'tipo': tipo, 'fecha': str(timezone.now())}
                }
            )
    else:
        Notificacion.objects.create(usuario=usuario, tipo=tipo, mensaje=mensaje, creada=timezone.now())
        rol = 'admin' if getattr(usuario, 'es_admin', False) else 'cliente'
        group_name = f"notificaciones_{rol}_{usuario.id}"
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'enviar_notificacion',
                'contenido': {'mensaje': mensaje, 'tipo': tipo, 'fecha': str(timezone.now())}
            }
        )
