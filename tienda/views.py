from rest_framework import generics, status, permissions, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import login, logout
from .models import (
    Usuario, Categoria, Subcategoria, Producto, Pedido, DetallePedido,
    Comentario, Calificacion, Like, Carrito, CarritoItem, 
    LikeComentario, Notificacion, HistorialAccion, EstadoVenta, Compra, DetalleCompra, 
)

from .serializers import (
    UsuarioSerializer, UsuarioPerfilSerializer, RegistroUsuarioSerializer, LoginSerializer,
    CategoriaSerializer, SubcategoriaSerializer, ProductoSerializer,
    PedidoSerializer, DetallePedidoSerializer, ComentarioSerializer,
    CalificacionSerializer, LikeSerializer, NotificacionSerializer,
    HistorialAccionSerializer, CarritoSerializer, EstadoVentaSerializer, 
)
from .cart import Cart
from .utils_pdf import generar_pdf_pedido
from django.http import HttpResponse
from .stats import historial_compras, ventas_por_dia, productos_mas_vendidos, mejores_clientes
from .notificaciones import notificar_usuario
import logging

logger = logging.getLogger(__name__)

from rest_framework import generics

from rest_framework.pagination import PageNumberPagination
from .models import Notificacion
from .serializers import NotificacionSerializer, CarritoSerializer
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class NotificacionListView(ListAPIView):
    serializer_class = NotificacionSerializer
    permission_classes = [IsAuthenticated]
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

class NotificacionMarkReadView(APIView):
    permission_classes = [IsAuthenticated]
    def patch(self, request, pk):
        try:
            noti = Notificacion.objects.get(pk=pk, usuario=request.user, eliminada=False)
            noti.leida = True
            noti.save()
            return Response({'success': 'Notificación marcada como leída.'})
        except Notificacion.DoesNotExist:
            return Response({'error': 'Notificación no encontrada.'}, status=404)

class NotificacionDeleteView(APIView):
    permission_classes = [IsAuthenticated]
    def delete(self, request, pk):
        try:
            noti = Notificacion.objects.get(pk=pk, usuario=request.user, eliminada=False)
            noti.eliminada = True
            noti.save()
            return Response({'success': 'Notificación eliminada.'})
        except Notificacion.DoesNotExist:
            return Response({'error': 'Notificación no encontrada.'}, status=404)

# --- Foro de comentarios (comentarios, respuestas, edición, eliminación, likes) ---
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
            # Notificar al admin y al usuario al que se responde (si aplica)
            admin = Usuario.objects.filter(es_admin=True, esta_activo=True).first()
            if admin:
                Notificacion.objects.create(usuario=admin, tipo='nuevo_comentario', mensaje=f'Nuevo comentario: {comentario.texto[:40]}...')
                from .notificaciones import notificar_usuario
                notificar_usuario('admin', admin.id, {
                    'tipo': 'nuevo_comentario',
                    'mensaje': f'Nuevo comentario: {comentario.texto[:40]}...'
                })
            if comentario.comentario_padre and comentario.comentario_padre.usuario != request.user:
                Notificacion.objects.create(usuario=comentario.comentario_padre.usuario, tipo='respuesta_comentario', mensaje=f'Tienes una respuesta a tu comentario.')
                from .notificaciones import notificar_usuario
                notificar_usuario('cliente', comentario.comentario_padre.usuario.id, {
                    'tipo': 'respuesta_comentario',
                    'mensaje': 'Tienes una respuesta a tu comentario.'
                })
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
            # Notificar al autor del comentario si no es el mismo usuario
            if comentario.usuario != request.user:
                Notificacion.objects.create(usuario=comentario.usuario, tipo='like_comentario', mensaje='Alguien dio like a tu comentario.')
                from .notificaciones import notificar_usuario
                notificar_usuario('cliente', comentario.usuario.id, {
                    'tipo': 'like_comentario',
                    'mensaje': 'Alguien dio like a tu comentario.'
                })
            return Response({'success': 'Like agregado.'})
        else:
            like.delete()
            return Response({'success': 'Like eliminado.'})

# --- Notificaciones persistentes ---
class NotificacionListView(generics.ListAPIView):
    serializer_class = NotificacionSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        return Notificacion.objects.filter(usuario=self.request.user, eliminada=False).order_by('-creada')

class NotificacionDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, pk):
        noti = Notificacion.objects.filter(id=pk, usuario=request.user).first()
        if not noti:
            return Response({'error': 'No encontrada'}, status=404)
        noti.eliminada = True
        noti.save()
        return Response({'success': 'Notificación eliminada.'})

class NotificacionMarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, pk):
        noti = Notificacion.objects.filter(id=pk, usuario=request.user).first()
        if not noti:
            return Response({'error': 'No encontrada'}, status=404)
        noti.leida = True
        noti.save()
        return Response({'success': 'Notificación marcada como leída.'})

# Carrito de compras en sesión
class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Carrito persistente profesional
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
        """
        Recibe lista de items: [{"producto_id": int, "cantidad": int}]
        Suma cantidades si ya existen, valida stock, ignora productos inexistentes/inactivos.
        """
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
from django.utils import timezone
from datetime import timedelta

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        numero = request.data.get('numero')
        ip = request.META.get('REMOTE_ADDR')
        try:
            user = Usuario.objects.get(numero=numero)
        except Usuario.DoesNotExist:
            user = None
        # Verifica bloqueo
        if user and user.bloqueado_hasta and user.bloqueado_hasta > timezone.now():
            return Response({'error': 'Cuenta bloqueada temporalmente. Intenta de nuevo más tarde.'}, status=403)
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            if not user.esta_activo:
                logger.warning(f"Intento de login de usuario desactivado: {user.numero}")
                return Response({'error': 'Usuario desactivado.'}, status=status.HTTP_403_FORBIDDEN)
            # Reset intentos fallidos y bloqueo
            user.intentos_fallidos = 0
            user.bloqueado_hasta = None
            user.ultimo_login_exitoso = timezone.now()
            user.ultimo_ip = ip
            user.save()
            login(request, user)
            logger.info(f"Usuario logueado: {user.numero}")
            HistorialAccion.objects.create(usuario=user, accion='login', ip=ip)
            return Response(UsuarioSerializer(user).data)
        # Si llega aquí, login fallido
        if user:
            user.intentos_fallidos += 1
            if user.intentos_fallidos >= 5:
                user.bloqueado_hasta = timezone.now() + timedelta(minutes=5)
                HistorialAccion.objects.create(usuario=user, accion='bloqueo temporal', detalle='5 intentos fallidos', ip=ip)
            user.save()
            logger.warning(f"Login fallido para {user.numero} (intentos: {user.intentos_fallidos})")
        return Response({'error': 'Número o contraseña incorrectos.'}, status=status.HTTP_400_BAD_REQUEST)

# Logout
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        logger.info(f"Usuario cerró sesión: {request.user.numero}")
        HistorialAccion.objects.create(usuario=request.user, accion='logout', ip=request.META.get('REMOTE_ADDR'))
        logout(request)
        return Response({'success': 'Sesión cerrada correctamente.'})

# Recuperación y cambio de contraseña
from django.core.cache import cache
import random

class RecuperarPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        numero = request.data.get('numero')
        try:
            user = Usuario.objects.get(numero=numero)
        except Usuario.DoesNotExist:
            return Response({'error': 'Usuario no encontrado.'}, status=404)
        codigo = str(random.randint(100000, 999999))
        cache.set(f"recuperar_{numero}", codigo, timeout=300)  # 5 minutos
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

# --- HISTORIAL DE ACCIONES ---
from rest_framework.pagination import PageNumberPagination
from .serializers import HistorialAccionSerializer

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

# Búsqueda avanzada de productos y destacados
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status

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
        # Ordenamiento seguro
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
        # Permite reutilizar los mismos filtros avanzados si se desea
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
        # Ordenamiento seguro
        ordering_fields = ['nombre', 'precio', 'stock', 'fecha_creacion']
        if ordering.lstrip('-') not in ordering_fields:
            ordering = '-fecha_creacion'
        queryset = queryset.order_by(ordering)
        paginator = ProductoPagination()
        page = paginator.paginate_queryset(queryset, request)
        logger.info(f"Listado de destacados. Params: {request.query_params}")
        return paginator.get_paginated_response(ProductoSerializer(page, many=True).data)

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
        # Crear pedido
        pedido = Pedido.objects.create(
            usuario=usuario,
            total=sum(item.producto.precio * item.cantidad for item in carrito.items.all()),
            estado='pendiente',
        )
        detalles = []
        for item in carrito.items.select_related('producto'):
            DetallePedido.objects.create(
                pedido=pedido,
                producto=item.producto,
                cantidad=item.cantidad,
                precio_unitario=item.producto.precio,
            )
            # Descontar stock y desactivar si llega a 0
            item.producto.stock -= item.cantidad
            if item.producto.stock == 0:
                item.producto.activo = False
            item.producto.save()
            detalles.append({
                'producto': item.producto.nombre,
                'cantidad': item.cantidad,
                'precio_unitario': float(item.producto.precio)
            })
            # Notificación admin si stock bajo
            if item.producto.stock <= 5:
                from .notificaciones import notificar_usuario
                notificar_usuario(None, f'Stock bajo para {item.producto.nombre}: {item.producto.stock} unidades.', tipo='stock_bajo')
        # Limpiar carrito
        carrito.items.all().delete()
        # Generar factura PDF
        pdf_content = generar_pdf_pedido(pedido)
        pdf_filename = f'factura_{pedido.id}.pdf'
        pedido.factura.save(pdf_filename, pdf_content)
        pedido.save()
        # Notificación usuario
        from .notificaciones import notificar_usuario
        notificar_usuario(usuario, f'¡Compra exitosa! Pedido #{pedido.id} registrado.', tipo='compra_exitosa')
        logger.info(f"Pedido #{pedido.id} creado para usuario {usuario.numero}")
        return Response({
            'success': f'Compra realizada correctamente. Pedido #{pedido.id}',
            'pedido_id': pedido.id,
            'factura_url': pedido.factura.url,
            'detalles': detalles
        })

class ComprasUsuarioView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        usuario = request.user
        pedidos = Pedido.objects.filter(usuario=usuario).order_by('-fecha')
        # Filtros opcionales
        estado = request.query_params.get('estado')
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')
        if estado:
            pedidos = pedidos.filter(estado=estado)
        if fecha_inicio:
            pedidos = pedidos.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            pedidos = pedidos.filter(fecha__lte=fecha_fin)
        # Paginación profesional
        from rest_framework.pagination import PageNumberPagination
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

from django.db.models import Q
from rest_framework.permissions import IsAdminUser

class ComprasAdminView(APIView):
    permission_classes = [IsAdminUser]
    def get(self, request):
        pedidos = Pedido.objects.all().order_by('-fecha')
        # Filtros opcionales
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
        # Paginación profesional
        from rest_framework.pagination import PageNumberPagination
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

# Estadísticas para clientes
class ClienteStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        data = historial_compras(request.user)
        logger.info(f"Usuario {request.user.numero} consultó sus estadísticas de compras.")
        return Response(data)

# Estadísticas para admin
class AdminStatsView(APIView):
    permission_classes = [permissions.IsAdminUser]
    def get(self, request):
        ventas = ventas_por_dia()
        productos = productos_mas_vendidos()
        clientes = mejores_clientes()
        logger.info(f"Admin {request.user.numero} consultó estadísticas globales.")
        return Response({
            'ventas_por_dia': ventas,
            'productos_mas_vendidos': productos,
            'mejores_clientes': clientes
        })

# CRUD de modelos principales

class EstadoVentaViewSet(viewsets.ModelViewSet):
    serializer_class = EstadoVentaSerializer
    queryset = EstadoVenta.objects.all()
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        if self.request.user.is_authenticated and getattr(self.request.user, 'es_admin', False):
            return EstadoVenta.objects.all()
        # Solo lectura para clientes: solo estados activos
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
            # Filtros avanzados para admin
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
        # Cliente: solo sus compras
        return qs.filter(usuario=user).order_by('-creado')

    def perform_create(self, serializer):
        # Solo admin puede crear compras (ingreso de inventario)
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
        # Cliente: solo detalles de sus compras
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

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and getattr(request.user, 'es_admin', False))

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
        from .models import Notificacion, Usuario
        from .notificaciones import notificar_usuario as notificar_ws
        # Solo el dueño o admin puede eliminar
        if instance.usuario != self.request.user and not getattr(self.request.user, 'es_admin', False):
            logger.warning(f"Usuario {self.request.user.numero} intentó eliminar pedido ajeno #{instance.id}")
            raise PermissionDenied("Solo puedes eliminar tus propios pedidos.")
        # Notificación a cliente y admin
        mensaje_cliente = f'Tu pedido #{instance.id} ha sido cancelado/eliminado.'
        mensaje_admin = f'El pedido #{instance.id} de {instance.usuario.nombre} ha sido cancelado/eliminado.'
        # Notifica y guarda para el cliente
        Notificacion.objects.create(
            usuario=instance.usuario,
            tipo='pedido_cancelado',
            mensaje=mensaje_cliente
        )
        notificar_ws(instance.usuario, mensaje_cliente, tipo='pedido_cancelado')
        # Notifica y guarda para el admin (si aplica)
        if getattr(self.request.user, 'es_admin', False):
            Notificacion.objects.create(
                usuario=self.request.user,
                tipo='pedido_cancelado',
                mensaje=mensaje_admin
            )
            notificar_ws(self.request.user, mensaje_admin, tipo='pedido_cancelado')
        instance.delete()
        logger.info(f"Pedido #{instance.id} eliminado/cancelado y notificaciones enviadas.")

class PedidoViewSet(viewsets.ModelViewSet):
    serializer_class = PedidoSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Pedido.objects.all()

    def get_queryset(self):
        if getattr(self.request.user, 'es_admin', False):
            return Pedido.objects.all()
        return Pedido.objects.filter(usuario=self.request.user)

    def perform_create(self, serializer):
        from .models import Notificacion, Usuario
        from .notificaciones import notificar_usuario as notificar_ws
        # Permitir que el admin registre pedidos para cualquier cliente
        if getattr(self.request.user, 'es_admin', False):
            data = self.request.data.copy()
            numero = data.get('numero')
            nombre = data.get('nombre')
            apellido = data.get('apellido')
            if not numero or not nombre or not apellido:
                raise PermissionDenied("Debe proporcionar número, nombre y apellido del cliente.")
            usuario = Usuario.objects.filter(numero=numero).first()
            nuevo_cliente = False
            if not usuario:
                usuario = Usuario.objects.create_user(
                    numero=numero,
                    nombre=nombre,
                    apellido=apellido,
                    password=numero
                )
                logger.info(f"Cliente creado automáticamente por admin {self.request.user.numero}: {numero}")
                nuevo_cliente = True
            pedido = serializer.save(usuario=usuario, creado_por=self.request.user)
            logger.info(f"Pedido registrado por admin {self.request.user.numero} para cliente {usuario.numero}")
            # Notificación persistente y en tiempo real para el cliente
            mensaje_cliente = (
                f'Se ha registrado un pedido a tu nombre. Puedes iniciar sesión usando tu número como contraseña.'
                if nuevo_cliente else f'Se ha registrado un nuevo pedido a tu nombre.'
            )
            Notificacion.objects.create(
                usuario=usuario,
                tipo='nuevo_pedido',
                mensaje=mensaje_cliente
            )
            notificar_ws(usuario, mensaje_cliente, tipo='nuevo_pedido')
            # Notificación persistente y en tiempo real para el admin
            mensaje_admin = f'Has registrado un pedido para el cliente {usuario.nombre} ({usuario.numero}).'
            Notificacion.objects.create(
                usuario=self.request.user,
                tipo='nuevo_pedido',
                mensaje=mensaje_admin
            )
            notificar_ws(self.request.user, mensaje_admin, tipo='nuevo_pedido')
            return
        # Clientes normales: lógica previa
        pedido = serializer.save(usuario=self.request.user)
        logger.info(f"Pedido creado por usuario {self.request.user.numero}")
        # Notificar a todos los admins activos
        admins = Usuario.objects.filter(es_admin=True, esta_activo=True)
        for admin in admins:
            mensaje_admin = f'Nuevo pedido #{pedido.id} realizado por {self.request.user.nombre}.'
            Notificacion.objects.create(
                usuario=admin,
                tipo='nuevo_pedido',
                mensaje=mensaje_admin
            )
            notificar_ws(admin, mensaje_admin, tipo='nuevo_pedido')
        # Notificar y guardar para el cliente
        mensaje_cliente = f'Tu pedido #{pedido.id} ha sido registrado exitosamente.'
        Notificacion.objects.create(
            usuario=self.request.user,
            tipo='nuevo_pedido',
            mensaje=mensaje_cliente
        )
        notificar_ws(self.request.user, mensaje_cliente, tipo='nuevo_pedido')

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.usuario != self.request.user and not getattr(self.request.user, 'es_admin', False):
            logger.warning(f"Usuario {self.request.user.numero} intentó editar pedido ajeno #{instance.id}")
            raise PermissionDenied("Solo puedes editar tus propios pedidos.")
        old_estado = instance.estado
        pedido_actualizado = serializer.save()
        # Notificación profesional a cliente y admin sobre cambio de estado
        if getattr(self.request.user, 'es_admin', False):
            nuevo_estado = serializer.validated_data.get("estado", old_estado)
            mensaje_cliente = f'El estado de tu pedido #{instance.id} ha cambiado a {nuevo_estado}.'
            mensaje_admin = f'Se ha actualizado el estado del pedido #{instance.id} de {instance.usuario.nombre} a {nuevo_estado}.'
            # Notifica y guarda en panel del cliente
            from .models import Notificacion, Usuario
            from .notificaciones import notificar_usuario as notificar_ws
            Notificacion.objects.create(
                usuario=instance.usuario,
                tipo='estado_pedido',
                mensaje=mensaje_cliente
            )
            notificar_ws(instance.usuario, mensaje_cliente, tipo='estado_pedido')
            # Notifica y guarda en panel del admin que realizó la acción
            Notificacion.objects.create(
                usuario=self.request.user,
                tipo='estado_pedido',
                mensaje=mensaje_admin
            )
            notificar_ws(self.request.user, mensaje_admin, tipo='estado_pedido')
            logger.info(f"Cambio de estado de pedido #{instance.id} notificado a cliente y admin.")


    # Endpoint para descargar PDF del pedido
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.query_params.get('pdf') == '1':
            # Solo el dueño del pedido o admin puede descargar
            if request.user != instance.usuario and not getattr(request.user, 'es_admin', False):
                logger.warning(f"Usuario {request.user.numero} intentó acceder a PDF de pedido ajeno #{instance.id}")
                return HttpResponse('No autorizado', status=403)
            pdf = generar_pdf_pedido(instance)
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename=\"pedido_{instance.id}.pdf\"'
            logger.info(f"PDF de pedido #{instance.id} descargado por usuario {request.user.numero}")
            return response
        return super().retrieve(request, *args, **kwargs)

class DetallePedidoViewSet(viewsets.ModelViewSet):
    serializer_class = DetallePedidoSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = DetallePedido.objects.all()

    def get_queryset(self):
        if getattr(self.request.user, 'es_admin', False):
            return DetallePedido.objects.all()
        return DetallePedido.objects.filter(pedido__usuario=self.request.user)

    def perform_create(self, serializer):
        if getattr(self.request.user, 'es_admin', False):
            raise PermissionDenied("Solo clientes pueden añadir detalles de pedido.")
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

class ComentarioViewSet(viewsets.ModelViewSet):
    serializer_class = ComentarioSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Comentario.objects.all()

    def get_queryset(self):
        return Comentario.objects.filter(producto__activo=True)

    def perform_create(self, serializer):
        from .models import Notificacion, Usuario
        from .notificaciones import notificar_usuario as notificar_ws
        comentario = serializer.save(usuario=self.request.user)
        logger.info(f"Comentario creado por usuario {self.request.user.numero}")
        # Notificación persistente y en tiempo real para admin
        admins = Usuario.objects.filter(es_admin=True, esta_activo=True)
        for admin in admins:
            mensaje_admin = f'Nuevo comentario en producto #{comentario.producto.id} por {self.request.user.nombre}.'
            Notificacion.objects.create(usuario=admin, tipo='nuevo_comentario', mensaje=mensaje_admin)
            notificar_ws(admin, mensaje_admin, tipo='nuevo_comentario')
        # Notificar al dueño del producto
        if hasattr(comentario.producto, 'usuario') and comentario.producto.usuario:
            mensaje_cliente = f'Nuevo comentario en tu producto #{comentario.producto.id} por {self.request.user.nombre}.'
            Notificacion.objects.create(usuario=comentario.producto.usuario, tipo='nuevo_comentario', mensaje=mensaje_cliente)
            notificar_ws(comentario.producto.usuario, mensaje_cliente, tipo='nuevo_comentario')


    def perform_update(self, serializer):
        from .models import Notificacion
        from .notificaciones import notificar_usuario as notificar_ws
        instance = self.get_object()
        if instance.usuario != self.request.user:
            logger.warning(f"Usuario {self.request.user.numero} intentó editar comentario ajeno #{instance.id}")
            raise PermissionDenied("Solo puedes editar tus propios comentarios.")
        serializer.save()
        # Notificación para el usuario que edita
        mensaje = f'Has actualizado tu comentario #{instance.id}.'
        Notificacion.objects.create(usuario=self.request.user, tipo='comentario_actualizado', mensaje=mensaje)
        notificar_ws(self.request.user, mensaje, tipo='comentario_actualizado')


    def perform_destroy(self, instance):
        from .models import Notificacion
        from .notificaciones import notificar_usuario as notificar_ws
        if instance.usuario != self.request.user:
            logger.warning(f"Usuario {self.request.user.numero} intentó eliminar comentario ajeno #{instance.id}")
            raise PermissionDenied("Solo puedes eliminar tus propios comentarios.")
        # Notificación para el usuario que elimina
        mensaje = f'Has eliminado tu comentario #{instance.id}.'
        Notificacion.objects.create(usuario=self.request.user, tipo='comentario_eliminado', mensaje=mensaje)
        notificar_ws(self.request.user, mensaje, tipo='comentario_eliminado')
        instance.delete()


class CalificacionViewSet(viewsets.ModelViewSet):
    serializer_class = CalificacionSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Calificacion.objects.all()

    def get_queryset(self):
        return Calificacion.objects.filter(producto__activo=True)

    def perform_create(self, serializer):
        from .models import Notificacion, Usuario
        from .notificaciones import notificar_usuario as notificar_ws
        calificacion = serializer.save(usuario=self.request.user)
        logger.info(f"Calificación creada por usuario {self.request.user.numero}")
        # Notificación persistente y en tiempo real para admin
        admins = Usuario.objects.filter(es_admin=True, esta_activo=True)
        for admin in admins:
            mensaje_admin = f'Nueva calificación en producto #{calificacion.producto.id} por {self.request.user.nombre}.'
            Notificacion.objects.create(usuario=admin, tipo='nueva_calificacion', mensaje=mensaje_admin)
            notificar_ws(admin, mensaje_admin, tipo='nueva_calificacion')
        # Notificar al dueño del producto
        if hasattr(calificacion.producto, 'usuario') and calificacion.producto.usuario:
            mensaje_cliente = f'Nueva calificación en tu producto #{calificacion.producto.id} por {self.request.user.nombre}.'
            Notificacion.objects.create(usuario=calificacion.producto.usuario, tipo='nueva_calificacion', mensaje=mensaje_cliente)
            notificar_ws(calificacion.producto.usuario, mensaje_cliente, tipo='nueva_calificacion')


    def perform_update(self, serializer):
        from .models import Notificacion
        from .notificaciones import notificar_usuario as notificar_ws
        instance = self.get_object()
        if instance.usuario != self.request.user:
            logger.warning(f"Usuario {self.request.user.numero} intentó editar calificación ajena #{instance.id}")
            raise PermissionDenied("Solo puedes editar tus propias calificaciones.")
        serializer.save()
        # Notificación para el usuario que edita
        mensaje = f'Has actualizado tu calificación #{instance.id}.'
        Notificacion.objects.create(usuario=self.request.user, tipo='calificacion_actualizada', mensaje=mensaje)
        notificar_ws(self.request.user, mensaje, tipo='calificacion_actualizada')


    def perform_destroy(self, instance):
        from .models import Notificacion
        from .notificaciones import notificar_usuario as notificar_ws
        if instance.usuario != self.request.user:
            logger.warning(f"Usuario {self.request.user.numero} intentó eliminar calificación ajena #{instance.id}")
            raise PermissionDenied("Solo puedes eliminar tus propias calificaciones.")
        # Notificación para el usuario que elimina
        mensaje = f'Has eliminado tu calificación #{instance.id}.'
        Notificacion.objects.create(usuario=self.request.user, tipo='calificacion_eliminada', mensaje=mensaje)
        notificar_ws(self.request.user, mensaje, tipo='calificacion_eliminada')
        instance.delete()


class LikeViewSet(viewsets.ModelViewSet):
    serializer_class = LikeSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Like.objects.all()

    def get_queryset(self):
        return Like.objects.filter(producto__activo=True)

    def perform_create(self, serializer):
        from .models import Notificacion, Usuario
        from .notificaciones import notificar_usuario as notificar_ws
        like = serializer.save(usuario=self.request.user)
        logger.info(f"Like creado por usuario {self.request.user.numero}")
        # Notificación persistente y en tiempo real para admin
        admins = Usuario.objects.filter(es_admin=True, esta_activo=True)
        for admin in admins:
            mensaje_admin = f'Nuevo like en producto #{like.producto.id} por {self.request.user.nombre}.'
            Notificacion.objects.create(usuario=admin, tipo='nuevo_like', mensaje=mensaje_admin)
            notificar_ws(admin, mensaje_admin, tipo='nuevo_like')
        # Notificación para el cliente si el producto tiene dueño
        if hasattr(like.producto, 'usuario') and like.producto.usuario:
            mensaje_cliente = f'Alguien dio like a tu producto #{like.producto.id}.'
            Notificacion.objects.create(usuario=like.producto.usuario, tipo='nuevo_like', mensaje=mensaje_cliente)
            notificar_ws(like.producto.usuario, mensaje_cliente, tipo='nuevo_like')


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
