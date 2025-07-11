from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def notificar_usuario(rol, usuario_id, contenido):
    channel_layer = get_channel_layer()
    group_name = f"notificaciones_{rol}_{usuario_id}"
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'enviar_notificacion',
            'contenido': contenido
        }
    )
