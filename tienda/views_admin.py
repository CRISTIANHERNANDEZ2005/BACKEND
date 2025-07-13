from rest_framework import generics, status, permissions, viewsets, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .models import Usuario, Categoria, Subcategoria, Producto, EstadoVenta, Compra, DetalleCompra, Pedido, DetallePedido, Notificacion, HistorialAccion, ImagenProducto
from .serializers import CategoriaSerializer, SubcategoriaSerializer, ProductoSerializer, EstadoVentaSerializer, CompraSerializer, DetalleCompraSerializer, PedidoSerializer, DetallePedidoSerializer, NotificacionSerializer, HistorialAccionSerializer, ImagenProductoSerializer
from .utils_pdf import generar_pdf_pedido
from django.http import HttpResponse
from django.utils import timezone
import logging
logger = logging.getLogger(__name__)
from django.core.exceptions import PermissionDenied

# =========================
# Vistas de Administración (solo admin)
# =========================
# CRUD de categorías, subcategorías, productos, estados de venta, compras, detalles de compra, stats globales, pedidos globales, destacar productos, reordenar/subir imágenes, historial de acciones admin, tipos de acciones, vistas de admin para pedidos y detalles, imágenes de productos (gestión completa).
# (El resto del contenido ya está correctamente segmentado y no requiere lógica de cliente)

# Permisos personalizados
class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True;
        return bool(request.user and request.user.is_authenticated and getattr(request.user, 'es_admin', False))

# CRUD de modelos principales (solo admin)
class CategoriaViewSet(viewsets.ModelViewSet):
    serializer_class = CategoriaSerializer
    permission_classes = [IsAdminOrReadOnly]
    queryset = Categoria.objects.all()
    def get_queryset(self):
        return Categoria.objects.filter(activo=True)
class SubcategoriaViewSet(viewsets.ModelViewSet):
    serializer_class = SubcategoriaSerializer
    permission_classes = [IsAdminOrReadOnly]
    queryset = Subcategoria.objects.all()
    def get_queryset(self):
        return Subcategoria.objects.filter(activo=True, categoria__activo=True)
class ProductoViewSet(viewsets.ModelViewSet):
    serializer_class = ProductoSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Producto.objects.all()
    def get_queryset(self):
        return Producto.objects.filter(activo=True, stock__gt=0, categoria__activo=True, subcategoria__activo=True)
    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)
        logger.info(f"Producto creado por usuario {self.request.user.numero}")
    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.usuario != self.request.user:
            logger.warning(f"Usuario {self.request.user.numero} intentó editar producto ajeno #{instance.id}")
            raise PermissionDenied("Solo puedes editar tus propios productos.")
        serializer.save()
    def perform_destroy(self, instance):
        if instance.usuario != self.request.user and not getattr(self.request.user, 'es_admin', False):
            logger.warning(f"Usuario {self.request.user.numero} intentó eliminar pedido ajeno #{instance.id}")
            raise PermissionDenied("Solo puedes eliminar tus propios pedidos.")
        instance.delete()
        logger.info(f"Pedido #{instance.id} eliminado/cancelado y notificaciones enviadas.")
class EstadoVentaViewSet(viewsets.ModelViewSet):
    serializer_class = EstadoVentaSerializer
    queryset = EstadoVenta.objects.all()
    permission_classes = [permissions.IsAdminUser]
    def get_queryset(self):
        if self.request.user.is_authenticated and getattr(self.request.user, 'es_admin', False):
            return EstadoVenta.objects.all()
        return EstadoVenta.objects.filter(activo=True)
    def perform_create(self, serializer):
        serializer.save()
        logger.info(f"Estado de venta creado por admin {self.request.user.numero}")
    def perform_update(self, serializer):
        serializer.save()
        logger.info(f"Estado de venta actualizado por admin {self.request.user.numero}")
    def perform_destroy(self, instance):
        instance.activo = False
        instance.save()
        logger.info(f"Estado de venta desactivado por admin {self.request.user.numero}")
class CompraViewSet(viewsets.ModelViewSet):
    serializer_class = CompraSerializer
    queryset = Compra.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]
    def get_queryset(self):
        user = self.request.user
        qs = Compra.objects.filter(activo=True)
        if getattr(user, 'es_admin', False):
            usuario = self.request.query_params.get('usuario')
            fecha_min = self.request.query_params.get('fecha_min')
            fecha_max = self.request.query_params.get('fecha_max')
            if usuario:
                qs = qs.filter(usuario__numero=usuario)
            if fecha_min:
                qs = qs.filter(creado__gte=fecha_min)
            if fecha_max:
                qs = qs.filter(creado__lte=fecha_max)
            return qs.order_by('-creado')
        return qs.filter(usuario=user).order_by('-creado')
    def perform_create(self, serializer):
        if not getattr(self.request.user, 'es_admin', False):
            raise PermissionDenied("Solo el administrador puede registrar compras.")
        compra = serializer.save(usuario=self.request.user)
        logger.info(f"Compra registrada por admin {self.request.user.numero}")
    def perform_update(self, serializer):
        if not getattr(self.request.user, 'es_admin', False):
            raise PermissionDenied("Solo el administrador puede editar compras.")
        serializer.save()
        logger.info(f"Compra actualizada por admin {self.request.user.numero}")
    def perform_destroy(self, instance):
        if not getattr(self.request.user, 'es_admin', False):
            raise PermissionDenied("Solo el administrador puede eliminar compras.")
        instance.activo = False
        instance.save()
        logger.info(f"Compra desactivada por admin {self.request.user.numero}")
class DetalleCompraViewSet(viewsets.ModelViewSet):
    serializer_class = DetalleCompraSerializer
    queryset = DetalleCompra.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]
    def get_queryset(self):
        user = self.request.user
        qs = DetalleCompra.objects.all()
        if getattr(user, 'es_admin', False):
            return qs
        return qs.filter(compra__usuario=user)
    def perform_create(self, serializer):
        if not getattr(self.request.user, 'es_admin', False):
            raise PermissionDenied("Solo el administrador puede añadir detalles de compra.")
        serializer.save()
        logger.info(f"Detalle de compra registrado por admin {self.request.user.numero}")
    def perform_update(self, serializer):
        if not getattr(self.request.user, 'es_admin', False):
            raise PermissionDenied("Solo el administrador puede editar detalles de compra.")
        serializer.save()
        logger.info(f"Detalle de compra actualizado por admin {self.request.user.numero}")
    def perform_destroy(self, instance):
        if not getattr(self.request.user, 'es_admin', False):
            raise PermissionDenied("Solo el administrador puede eliminar detalles de compra.")
        instance.delete()
        logger.info(f"Detalle de compra eliminado por admin {self.request.user.numero}")
# Stats y gestión global admin
class ComprasAdminView(APIView):
    permission_classes = [permissions.IsAdminUser]
    def get(self, request):
        pedidos = Pedido.objects.all().order_by('-fecha')
        usuario = request.query_params.get('usuario')
        estado = request.query_params.get('estado')
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')
        if usuario:
            pedidos = pedidos.filter(usuario__numero__icontains=usuario)
        if estado:
            pedidos = pedidos.filter(estado=estado)
        if fecha_inicio:
            pedidos = pedidos.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            pedidos = pedidos.filter(fecha__lte=fecha_fin)
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(pedidos, request)
        data = []
        for pedido in page:
            detalles = DetallePedido.objects.filter(pedido=pedido)
            data.append({
                'id': pedido.id,
                'usuario': pedido.usuario.numero,
                'fecha': pedido.fecha,
                'estado': pedido.estado,
                'total': float(pedido.total),
                'factura_url': pedido.factura.url if pedido.factura else None,
                'detalles': [
                    {
                        'producto': d.producto.nombre,
                        'cantidad': d.cantidad,
                        'precio_unitario': float(d.precio_unitario)
                    } for d in detalles
                ]
            })
        return paginator.get_paginated_response(data)
class AdminStatsView(APIView):
    permission_classes = [permissions.IsAdminUser]
    def get(self, request):
        # Implementa tu lógica de stats globales aquí
        return Response({'stats': 'Estadísticas globales'})
class DestacarProductoView(APIView):
    permission_classes = [permissions.IsAdminUser]
    def patch(self, request, pk):
        try:
            producto = Producto.objects.get(pk=pk)
        except Producto.DoesNotExist:
            return Response({'error': 'Producto no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        destacado = request.data.get('destacado')
        if destacado is None:
            return Response({'error': 'Campo "destacado" requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        producto.destacado = bool(destacado)
        producto.save()
        logger.info(f"Admin {request.user.numero} cambió destacado de producto {producto.nombre} a {producto.destacado}")
        return Response({'success': f'El producto "{producto.nombre}" ahora tiene destacado={producto.destacado}.'})
# Imágenes de productos (gestión completa)
class ImagenProductoViewSet(viewsets.ModelViewSet):
    serializer_class = ImagenProductoSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ImagenProducto.objects.all()
    def get_queryset(self):
        if getattr(self.request.user, 'es_admin', False):
            return ImagenProducto.objects.all()
        return ImagenProducto.objects.filter(producto__activo=True)
    def perform_create(self, serializer):
        producto_id = self.request.data.get('producto')
        try:
            producto = Producto.objects.get(id=producto_id, activo=True)
        except Producto.DoesNotExist:
            raise serializers.ValidationError("Producto no encontrado o inactivo.")
        if not getattr(self.request.user, 'es_admin', False):
            raise PermissionDenied("Solo administradores pueden crear imágenes de productos.")
        imagen = serializer.save()
        logger.info(f"Imagen de producto creada por {self.request.user.numero} para producto {producto.nombre}")
    def perform_update(self, serializer):
        instance = self.get_object()
        if not getattr(self.request.user, 'es_admin', False):
            raise PermissionDenied("Solo administradores pueden editar imágenes de productos.")
        imagen = serializer.save()
        logger.info(f"Imagen de producto actualizada por {self.request.user.numero}")
    def perform_destroy(self, instance):
        if not getattr(self.request.user, 'es_admin', False):
            raise PermissionDenied("Solo administradores pueden eliminar imágenes de productos.")
        producto_nombre = instance.producto.nombre
        instance.delete()
        logger.info(f"Imagen de producto eliminada por {self.request.user.numero} del producto {producto_nombre}")
class ReordenarImagenesView(APIView):
    permission_classes = [permissions.IsAdminUser]
    def post(self, request, producto_id):
        try:
            producto = Producto.objects.get(id=producto_id, activo=True)
        except Producto.DoesNotExist:
            return Response({'error': 'Producto no encontrado o inactivo.'}, status=status.HTTP_404_NOT_FOUND)
        orden_imagenes = request.data.get('orden_imagenes', [])
        if not isinstance(orden_imagenes, list):
            return Response({'error': 'El campo orden_imagenes debe ser una lista.'}, status=status.HTTP_400_BAD_REQUEST)
        imagenes_existentes = ImagenProducto.objects.filter(producto=producto)
        ids_existentes = set(imagenes_existentes.values_list('id', flat=True))
        ids_solicitados = set(orden_imagenes)
        if not ids_solicitados.issubset(ids_existentes):
            return Response({'error': 'Algunos IDs de imágenes no existen o no pertenecen al producto.'}, status=status.HTTP_400_BAD_REQUEST)
        for orden, imagen_id in enumerate(orden_imagenes):
            ImagenProducto.objects.filter(id=imagen_id, producto=producto).update(orden=orden)
        logger.info(f"Imágenes del producto {producto.nombre} reordenadas por {request.user.numero}")
        imagenes_actualizadas = ImagenProducto.objects.filter(producto=producto).order_by('orden')
        serializer = ImagenProductoSerializer(imagenes_actualizadas, many=True)
        return Response({
            'message': 'Imágenes reordenadas exitosamente.',
            'imagenes': serializer.data
        })
class SubirImagenesProductoView(APIView):
    permission_classes = [permissions.IsAdminUser]
    def post(self, request, producto_id):
        try:
            producto = Producto.objects.get(id=producto_id, activo=True)
        except Producto.DoesNotExist:
            return Response({'error': 'Producto no encontrado o inactivo.'}, status=status.HTTP_404_NOT_FOUND)
        imagenes = request.FILES.getlist('imagenes')
        descripciones = request.data.getlist('descripciones', [])
        if not imagenes:
            return Response({'error': 'No se proporcionaron imágenes.'}, status=status.HTTP_400_BAD_REQUEST)
        imagenes_creadas = []
        errores = []
        ultimo_orden = ImagenProducto.objects.filter(producto=producto).aggregate(
            models.Max('orden')
        )['orden__max'] or -1
        for i, imagen in enumerate(imagenes):
            try:
                descripcion = descripciones[i] if i < len(descripciones) else ''
                nueva_imagen = ImagenProducto.objects.create(
                    producto=producto,
                    imagen=imagen,
                    descripcion=descripcion,
                    orden=ultimo_orden + 1 + i
                )
                imagenes_creadas.append(ImagenProductoSerializer(nueva_imagen).data)
            except Exception as e:
                errores.append(f"Error al procesar imagen {i+1}: {str(e)}")
        logger.info(f"{len(imagenes_creadas)} imágenes subidas al producto {producto.nombre} por {request.user.numero}")
        response_data = {
            'message': f'{len(imagenes_creadas)} imágenes subidas exitosamente.',
            'imagenes_creadas': imagenes_creadas
        }
        if errores:
            response_data['errores'] = errores
        return Response(response_data, status=status.HTTP_201_CREATED)
# Historial y tipos de acciones admin
class HistorialAccionAdminView(generics.ListAPIView):
    serializer_class = HistorialAccionSerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = PageNumberPagination
    def get_queryset(self):
        qs = HistorialAccion.objects.all().order_by('-fecha')
        usuario = self.request.query_params.get('usuario')
        accion = self.request.query_params.get('accion')
        if usuario:
            qs = qs.filter(usuario__numero=usuario)
        if accion:
            qs = qs.filter(accion=accion)
        return qs
    
class AccionesDisponiblesView(APIView):
    permission_classes = [permissions.IsAdminUser]
    def get(self, request):
        acciones = HistorialAccion.objects.values_list('accion', flat=True).distinct()
        return Response(sorted(set(acciones))) 