from rest_framework import generics, status, permissions, viewsets, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .models import Usuario, Producto, Pedido, DetallePedido, Comentario, Calificacion, Like, Carrito, CarritoItem, LikeComentario, Notificacion, HistorialAccion, ImagenProducto
from .serializers import UsuarioSerializer, UsuarioPerfilSerializer, RegistroUsuarioSerializer, LoginSerializer, ProductoSerializer, PedidoSerializer, DetallePedidoSerializer, ComentarioSerializer, CalificacionSerializer, LikeSerializer, NotificacionSerializer, HistorialAccionSerializer, CarritoSerializer, ImagenProductoSerializer
from .cart import Cart
from .utils_pdf import generar_pdf_pedido
from django.contrib.auth import login, logout
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import random
import logging
logger = logging.getLogger(__name__)

# Registro de usuario (solo clientes)
class RegistroUsuarioView(generics.CreateAPIView):
    serializer_class = RegistroUsuarioSerializer
    permission_classes = [permissions.AllowAny]
    def perform_create(self, serializer):
        try:
            user = serializer.save()
            logger.info(f"Nuevo usuario registrado: {user.numero}")
        except Exception as e:
            logger.error(f"Error al registrar usuario: {e}")
            raise

# Login personalizado con número
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        numero = request.data.get('numero')
        ip = request.META.get('REMOTE_ADDR')
        try:
            user = Usuario.objects.get(numero=numero)
        except Usuario.DoesNotExist:
            user = None
        if user and user.bloqueado_hasta and user.bloqueado_hasta > timezone.now():
            return Response({'error': 'Cuenta bloqueada temporalmente. Intenta de nuevo más tarde.'}, status=403)
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            if not user.esta_activo:
                logger.warning(f"Intento de login de usuario desactivado: {user.numero}")
                return Response({'error': 'Usuario desactivado.'}, status=status.HTTP_403_FORBIDDEN)
            user.intentos_fallidos = 0
            user.bloqueado_hasta = None
            user.ultimo_login_exitoso = timezone.now()
            user.ultimo_ip = ip
            user.save()
            login(request, user)
            logger.info(f"Usuario logueado: {user.numero}")
            HistorialAccion.objects.create(usuario=user, accion='login', ip=ip)
            return Response(UsuarioSerializer(user).data)
        if user:
            user.intentos_fallidos += 1
            if user.intentos_fallidos >= 5:
                user.bloqueado_hasta = timezone.now() + timedelta(minutes=5)
                HistorialAccion.objects.create(usuario=user, accion='bloqueo temporal', detalle='5 intentos fallidos', ip=ip)
            user.save()
            logger.warning(f"Login fallido para {user.numero} (intentos: {user.intentos_fallidos})")
        return Response({'error': 'Número o contraseña incorrectos.'}, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        logger.info(f"Usuario cerró sesión: {request.user.numero}")
        HistorialAccion.objects.create(usuario=request.user, accion='logout', ip=request.META.get('REMOTE_ADDR'))
        logout(request)
        return Response({'success': 'Sesión cerrada correctamente.'})

# Recuperación y cambio de contraseña
class RecuperarPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        numero = request.data.get('numero')
        try:
            user = Usuario.objects.get(numero=numero)
        except Usuario.DoesNotExist:
            return Response({'error': 'Usuario no encontrado.'}, status=404)
        codigo = str(random.randint(100000, 999999))
        cache.set(f"recuperar_{numero}", codigo, timeout=300)
        logger.info(f"[RECUPERACIÓN] Código para {numero}: {codigo}")
        HistorialAccion.objects.create(usuario=user, accion='solicitud recuperación', detalle=f'Código: {codigo}', ip=request.META.get('REMOTE_ADDR'))
        return Response({'success': 'Código enviado (simulado en log/servidor).'})

class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        numero = request.data.get('numero')
        codigo = request.data.get('codigo')
        nueva = request.data.get('nueva_password')
        real = cache.get(f"recuperar_{numero}")
        try:
            user = Usuario.objects.get(numero=numero)
        except Usuario.DoesNotExist:
            return Response({'error': 'Usuario no encontrado.'}, status=404)
        if not real or codigo != real:
            return Response({'error': 'Código inválido o expirado.'}, status=400)
        user.set_password(nueva)
        user.save()
        cache.delete(f"recuperar_{numero}")
        HistorialAccion.objects.create(usuario=user, accion='reset password', ip=request.META.get('REMOTE_ADDR'))
        return Response({'success': 'Contraseña restablecida correctamente.'})

class CambiarPasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        actual = request.data.get('actual_password')
        nueva = request.data.get('nueva_password')
        if not request.user.check_password(actual):
            return Response({'error': 'Contraseña actual incorrecta.'}, status=400)
        request.user.set_password(nueva)
        request.user.save()
        HistorialAccion.objects.create(usuario=request.user, accion='cambio password', ip=request.META.get('REMOTE_ADDR'))
        return Response({'success': 'Contraseña cambiada correctamente.'})

# Gestión de perfil de usuario
class PerfilUsuarioView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        serializer = UsuarioPerfilSerializer(request.user)
        logger.info(f"Usuario {request.user.numero} visualizó su perfil.")
        return Response(serializer.data)
    def put(self, request):
        serializer = UsuarioPerfilSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Usuario {request.user.numero} actualizó su perfil.")
            return Response(serializer.data)
        logger.warning(f"Error al actualizar perfil de usuario {request.user.numero}: {serializer.errors}")
        return Response(serializer.errors, status=400)
    def delete(self, request):
        request.user.esta_activo = False
        request.user.save()
        logger.info(f"Usuario {request.user.numero} desactivó su cuenta.")
        return Response({'success': 'Cuenta desactivada.'})

# Carrito de compras en sesión
class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
        serializer = CarritoSerializer(carrito)
        logger.info(f"Usuario {request.user.numero} consultó su carrito persistente.")
        return Response(serializer.data)
    def post(self, request):
        producto_id = request.data.get('producto_id')
        cantidad = int(request.data.get('cantidad', 1))
        carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
        try:
            producto = Producto.objects.get(pk=producto_id, activo=True)
            if producto.stock < cantidad:
                return Response({'error': f'Solo hay {producto.stock} unidades disponibles.'}, status=400)
            item, created = CarritoItem.objects.get_or_create(carrito=carrito, producto=producto)
            if not created:
                item.cantidad += cantidad
            else:
                item.cantidad = cantidad
            item.save()
            logger.info(f"Producto {producto_id} añadido al carrito persistente de {request.user.numero}")
            return Response({'success': 'Producto añadido al carrito.'})
        except Producto.DoesNotExist:
            logger.error(f"Producto {producto_id} no existe o está inactivo.")
            return Response({'error': 'Producto no encontrado.'}, status=404)
        except Exception as e:
            logger.error(f"Error añadiendo producto al carrito persistente: {e}")
            return Response({'error': str(e)}, status=400)
    def delete(self, request):
        producto_id = request.data.get('producto_id')
        carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
        try:
            item = CarritoItem.objects.get(carrito=carrito, producto_id=producto_id)
            item.delete()
            logger.info(f"Producto {producto_id} eliminado del carrito persistente de {request.user.numero}")
            return Response({'success': 'Producto eliminado del carrito.'})
        except CarritoItem.DoesNotExist:
            return Response({'error': 'Producto no encontrado en el carrito.'}, status=404)

class CarritoMigrarView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        items = request.data.get('items', [])
        carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
        errores = []
        for entry in items:
            producto_id = entry.get('producto_id')
            cantidad = int(entry.get('cantidad', 1))
            try:
                producto = Producto.objects.get(pk=producto_id, activo=True)
                if producto.stock < cantidad:
                    errores.append({'producto_id': producto_id, 'error': f'Solo hay {producto.stock} disponibles.'})
                    continue
                item, created = CarritoItem.objects.get_or_create(carrito=carrito, producto=producto)
                if not created:
                    item.cantidad += cantidad
                else:
                    item.cantidad = cantidad
                item.save()
            except Producto.DoesNotExist:
                errores.append({'producto_id': producto_id, 'error': 'Producto no encontrado o inactivo.'})
        serializer = CarritoSerializer(carrito)
        logger.info(f"Carrito migrado desde LocalStorage para usuario {request.user.numero}")
        return Response({'carrito': serializer.data, 'errores': errores})

class CartClearView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        Cart(request).clear()
        logger.info(f"Carrito limpiado por {request.user.numero}")
        return Response({'success': 'Carrito limpiado.'})

# Notificaciones de usuario
class NotificacionListView(generics.ListAPIView):
    serializer_class = NotificacionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PageNumberPagination
    def get_queryset(self):
        qs = Notificacion.objects.filter(usuario=self.request.user, eliminada=False).order_by('-creada')
        leida = self.request.query_params.get('leida')
        tipo = self.request.query_params.get('tipo')
        if leida is not None:
            qs = qs.filter(leida=(leida == '1' or leida is True or leida == 'true'))
        if tipo:
            qs = qs.filter(tipo=tipo)
        return qs
class NotificacionDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def delete(self, request, pk):
        noti = Notificacion.objects.filter(pk=pk, usuario=request.user, eliminada=False).first()
        if not noti:
            return Response({'error': 'Notificación no encontrada.'}, status=404)
        noti.eliminada = True
        noti.save()
        return Response({'success': 'Notificación eliminada.'})
class NotificacionMarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def patch(self, request, pk):
        noti = Notificacion.objects.filter(pk=pk, usuario=request.user, eliminada=False).first()
        if not noti:
            return Response({'error': 'Notificación no encontrada.'}, status=404)
        noti.leida = True
        noti.save()
        return Response({'success': 'Notificación marcada como leída.'})

# Foro de comentarios (comentarios, respuestas, edición, eliminación, likes)
class ComentarioForoView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    def get(self, request):
        producto_id = request.query_params.get('producto')
        if producto_id:
            comentarios = Comentario.objects.filter(producto_id=producto_id, comentario_padre=None, activo=True)
        else:
            comentarios = Comentario.objects.filter(comentario_padre=None, activo=True)
        return Response(ComentarioSerializer(comentarios, many=True).data)
    def post(self, request):
        data = request.data.copy()
        data['usuario'] = request.user.id
        serializer = ComentarioSerializer(data=data)
        if serializer.is_valid():
            comentario = serializer.save()
            return Response(ComentarioSerializer(comentario).data, status=201)
        return Response(serializer.errors, status=400)
    def put(self, request):
        comentario_id = request.data.get('id')
        comentario = Comentario.objects.filter(id=comentario_id, usuario=request.user, activo=True).first()
        if not comentario:
            return Response({'error': 'No autorizado o comentario no existe.'}, status=403)
        serializer = ComentarioSerializer(comentario, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
    def delete(self, request):
        comentario_id = request.data.get('id')
        comentario = Comentario.objects.filter(id=comentario_id, usuario=request.user, activo=True).first()
        if not comentario:
            return Response({'error': 'No autorizado o comentario no existe.'}, status=403)
        comentario.activo = False
        comentario.save()
        return Response({'success': 'Comentario eliminado.'})
class LikeComentarioView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, comentario_id):
        comentario = Comentario.objects.filter(id=comentario_id, activo=True).first()
        if not comentario:
            return Response({'error': 'Comentario no encontrado'}, status=404)
        like, created = LikeComentario.objects.get_or_create(usuario=request.user, comentario=comentario)
        if created:
            return Response({'success': 'Like agregado.'})
        else:
            like.delete()
            return Response({'success': 'Like eliminado.'})

# CRUD de comentarios, calificaciones y likes (solo propios)
class ComentarioViewSet(viewsets.ModelViewSet):
    serializer_class = ComentarioSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Comentario.objects.all()
    def get_queryset(self):
        return Comentario.objects.filter(producto__activo=True)
    def perform_create(self, serializer):
        comentario = serializer.save(usuario=self.request.user)
        logger.info(f"Comentario creado por usuario {self.request.user.numero}")
    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.usuario != self.request.user:
            logger.warning(f"Usuario {self.request.user.numero} intentó editar comentario ajeno #{instance.id}")
            raise PermissionDenied("Solo puedes editar tus propios comentarios.")
        serializer.save()
    def perform_destroy(self, instance):
        if instance.usuario != self.request.user:
            logger.warning(f"Usuario {self.request.user.numero} intentó eliminar comentario ajeno #{instance.id}")
            raise PermissionDenied("Solo puedes eliminar tus propios comentarios.")
        instance.delete()
class CalificacionViewSet(viewsets.ModelViewSet):
    serializer_class = CalificacionSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Calificacion.objects.all()
    def get_queryset(self):
        return Calificacion.objects.filter(producto__activo=True)
    def perform_create(self, serializer):
        calificacion = serializer.save(usuario=self.request.user)
        logger.info(f"Calificación creada por usuario {self.request.user.numero}")
    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.usuario != self.request.user:
            logger.warning(f"Usuario {self.request.user.numero} intentó editar calificación ajena #{instance.id}")
            raise PermissionDenied("Solo puedes editar tus propias calificaciones.")
        serializer.save()
    def perform_destroy(self, instance):
        if instance.usuario != self.request.user:
            logger.warning(f"Usuario {self.request.user.numero} intentó eliminar calificación ajena #{instance.id}")
            raise PermissionDenied("Solo puedes eliminar tus propias calificaciones.")
        instance.delete()
class LikeViewSet(viewsets.ModelViewSet):
    serializer_class = LikeSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Like.objects.all()
    def get_queryset(self):
        return Like.objects.filter(producto__activo=True)
    def perform_create(self, serializer):
        like = serializer.save(usuario=self.request.user)
        logger.info(f"Like creado por usuario {self.request.user.numero}")
    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.usuario != self.request.user:
            logger.warning(f"Usuario {self.request.user.numero} intentó editar like ajeno #{instance.id}")
            raise PermissionDenied("Solo puedes editar tus propios likes.")
        serializer.save()
    def perform_destroy(self, instance):
        if instance.usuario != self.request.user:
            logger.warning(f"Usuario {self.request.user.numero} intentó eliminar like ajeno #{instance.id}")
            raise PermissionDenied("Solo puedes eliminar tus propios likes.")
        instance.delete()

# Compras y pedidos del usuario
class ComprarView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        usuario = request.user
        carrito = getattr(usuario, 'carrito', None)
        if not carrito or not carrito.items.exists():
            return Response({'error': 'El carrito está vacío.'}, status=400)
        productos_sin_stock = []
        for item in carrito.items.select_related('producto'):
            if not item.producto.activo or item.producto.stock < item.cantidad:
                productos_sin_stock.append({
                    'producto_id': item.producto.id,
                    'nombre': item.producto.nombre,
                    'stock': item.producto.stock,
                    'solicitado': item.cantidad
                })
        if productos_sin_stock:
            return Response({'error': 'Algunos productos no tienen stock suficiente.', 'productos': productos_sin_stock}, status=400)
        pedido = Pedido.objects.create(
            usuario=usuario,
            total=sum(item.producto.precio * item.cantidad for item in carrito.items.all()),
            estado='pendiente',
        )
        for item in carrito.items.select_related('producto'):
            DetallePedido.objects.create(
                pedido=pedido,
                producto=item.producto,
                cantidad=item.cantidad,
                precio_unitario=item.producto.precio,
            )
            item.producto.stock -= item.cantidad
            if item.producto.stock == 0:
                item.producto.activo = False
            item.producto.save()
        carrito.items.all().delete()
        pdf_content = generar_pdf_pedido(pedido)
        pdf_filename = f'factura_{pedido.id}.pdf'
        pedido.factura.save(pdf_filename, pdf_content)
        pedido.save()
        return Response({
            'success': f'Compra realizada correctamente. Pedido #{pedido.id}',
            'pedido_id': pedido.id,
            'factura_url': pedido.factura.url,
        })
class ComprasUsuarioView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        usuario = request.user
        pedidos = Pedido.objects.filter(usuario=usuario).order_by('-fecha')
        estado = request.query_params.get('estado')
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')
        if estado:
            pedidos = pedidos.filter(estado=estado)
        if fecha_inicio:
            pedidos = pedidos.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            pedidos = pedidos.filter(fecha__lte=fecha_fin)
        paginator = PageNumberPagination()
        paginator.page_size = 10
        page = paginator.paginate_queryset(pedidos, request)
        data = []
        for pedido in page:
            detalles = DetallePedido.objects.filter(pedido=pedido)
            data.append({
                'id': pedido.id,
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

# Historial de acciones del cliente
class HistorialAccionClienteView(generics.ListAPIView):
    serializer_class = HistorialAccionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PageNumberPagination
    def get_queryset(self):
        qs = self.request.user.historial_acciones.all().order_by('-fecha')
        accion = self.request.query_params.get('accion')
        if accion:
            qs = qs.filter(accion=accion)
        return qs

# Stats de cliente
class ClienteStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        # Implementa tu lógica de stats aquí
        return Response({'stats': 'Estadísticas de cliente'})

# Búsqueda avanzada de productos y destacados
class ProductoPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 50
class BusquedaProductoView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    def get(self, request):
        q = request.query_params.get('q', '')
        categoria = request.query_params.get('categoria')
        subcategoria = request.query_params.get('subcategoria')
        destacados = request.query_params.get('destacados')
        precio_min = request.query_params.get('precio_min')
        precio_max = request.query_params.get('precio_max')
        stock_min = request.query_params.get('stock_min')
        stock_max = request.query_params.get('stock_max')
        ordering = request.query_params.get('ordering', '-fecha_creacion')
        queryset = Producto.objects.filter(activo=True, stock__gt=0)
        if q:
            queryset = queryset.filter(nombre__icontains=q)
        if categoria:
            queryset = queryset.filter(subcategoria__categoria_id=categoria)
        if subcategoria:
            queryset = queryset.filter(subcategoria_id=subcategoria)
        if destacados == '1':
            queryset = queryset.filter(destacado=True)
        if precio_min:
            queryset = queryset.filter(precio__gte=precio_min)
        if precio_max:
            queryset = queryset.filter(precio__lte=precio_max)
        if stock_min:
            queryset = queryset.filter(stock__gte=stock_min)
        if stock_max:
            queryset = queryset.filter(stock__lte=stock_max)
        ordering_fields = ['nombre', 'precio', 'stock', 'fecha_creacion']
        if ordering.lstrip('-') not in ordering_fields:
            ordering = '-fecha_creacion'
        queryset = queryset.order_by(ordering)
        paginator = ProductoPagination()
        page = paginator.paginate_queryset(queryset, request)
        logger.info(f"Busqueda avanzada realizada. Params: {request.query_params}")
        return paginator.get_paginated_response(ProductoSerializer(page, many=True).data)
class ProductosDestacadosView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        ordering = request.query_params.get('ordering', '-fecha_creacion')
        queryset = Producto.objects.filter(activo=True, destacado=True, stock__gt=0)
        q = request.query_params.get('q', '')
        categoria = request.query_params.get('categoria')
        subcategoria = request.query_params.get('subcategoria')
        precio_min = request.query_params.get('precio_min')
        precio_max = request.query_params.get('precio_max')
        if q:
            queryset = queryset.filter(nombre__icontains=q)
        if categoria:
            queryset = queryset.filter(subcategoria__categoria_id=categoria)
        if subcategoria:
            queryset = queryset.filter(subcategoria_id=subcategoria)
        if precio_min:
            queryset = queryset.filter(precio__gte=precio_min)
        if precio_max:
            queryset = queryset.filter(precio__lte=precio_max)
        ordering_fields = ['nombre', 'precio', 'stock', 'fecha_creacion']
        if ordering.lstrip('-') not in ordering_fields:
            ordering = '-fecha_creacion'
        queryset = queryset.order_by(ordering)
        paginator = ProductoPagination()
        page = paginator.paginate_queryset(queryset, request)
        logger.info(f"Listado de destacados. Params: {request.query_params}")
        return paginator.get_paginated_response(ProductoSerializer(page, many=True).data)

# Pedidos y detalles de pedido del usuario
class PedidoViewSet(viewsets.ModelViewSet):
    serializer_class = PedidoSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Pedido.objects.all()
    def get_queryset(self):
        return Pedido.objects.filter(usuario=self.request.user)
    def perform_create(self, serializer):
        pedido = serializer.save(usuario=self.request.user)
        logger.info(f"Pedido creado por usuario {self.request.user.numero}")
    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.usuario != self.request.user:
            logger.warning(f"Usuario {self.request.user.numero} intentó editar pedido ajeno #{instance.id}")
            raise PermissionDenied("Solo puedes editar tus propios pedidos.")
        serializer.save()
    def perform_destroy(self, instance):
        if instance.usuario != self.request.user:
            logger.warning(f"Usuario {self.request.user.numero} intentó eliminar pedido ajeno #{instance.id}")
            raise PermissionDenied("Solo puedes eliminar tus propios pedidos.")
        instance.delete()
class DetallePedidoViewSet(viewsets.ModelViewSet):
    serializer_class = DetallePedidoSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = DetallePedido.objects.all()
    def get_queryset(self):
        return DetallePedido.objects.filter(pedido__usuario=self.request.user)
    def perform_create(self, serializer):
        detalle = serializer.save(usuario=self.request.user)
        producto = detalle.producto
        cantidad = detalle.cantidad
        if producto.stock < cantidad:
            logger.error(f"Stock insuficiente para producto {producto.nombre}. Stock: {producto.stock}, solicitado: {cantidad}")
            raise PermissionDenied(f"Stock insuficiente para {producto.nombre}.")
        producto.stock -= cantidad
        if producto.stock == 0:
            producto.activo = False
        producto.save()
        logger.info(f"Detalle de pedido creado y stock actualizado por usuario {self.request.user.numero}")

# Imágenes de productos (solo consulta)
class ImagenesProductoView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    def get(self, request, producto_id):
        try:
            producto = Producto.objects.get(id=producto_id, activo=True)
        except Producto.DoesNotExist:
            return Response({'error': 'Producto no encontrado o inactivo.'}, status=status.HTTP_404_NOT_FOUND)
        imagenes = ImagenProducto.objects.filter(producto=producto).order_by('orden')
        serializer = ImagenProductoSerializer(imagenes, many=True)
        return Response({
            'producto': {
                'id': producto.id,
                'nombre': producto.nombre
            },
            'imagenes': serializer.data
        }) 