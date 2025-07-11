from django.db.models import Sum, Count, F
from tienda.models import Pedido, DetallePedido, Producto, Usuario
from datetime import datetime, timedelta

# Estadísticas para clientes

def historial_compras(usuario):
    pedidos = Pedido.objects.filter(usuario=usuario).order_by('-fecha')
    total_gastado = pedidos.aggregate(total=Sum('total'))['total'] or 0
    cantidad_pedidos = pedidos.count()
    return {
        'cantidad_pedidos': cantidad_pedidos,
        'total_gastado': float(total_gastado),
        'historial': [
            {
                'id': p.id,
                'fecha': p.fecha,
                'total': float(p.total),
                'estado': p.estado
            } for p in pedidos
        ]
    }

# Estadísticas para admin

def ventas_por_dia(ultimos_n=30):
    hoy = datetime.now().date()
    dias = [(hoy - timedelta(days=i)) for i in range(ultimos_n)][::-1]
    ventas = Pedido.objects.filter(fecha__date__gte=dias[0], estado='completado')
    datos = {str(d): 0 for d in dias}
    for v in ventas:
        d = v.fecha.date()
        datos[str(d)] += float(v.total)
    return datos

def productos_mas_vendidos(top_n=5):
    qs = DetallePedido.objects.values('producto__nombre').annotate(
        total_vendidos=Sum('cantidad')).order_by('-total_vendidos')[:top_n]
    return list(qs)

def mejores_clientes(top_n=5):
    qs = Pedido.objects.values('usuario__numero', 'usuario__nombre', 'usuario__apellido').annotate(
        total_gastado=Sum('total'), cantidad=Count('id')).order_by('-total_gastado')[:top_n]
    return list(qs)
