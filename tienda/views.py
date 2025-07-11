from rest_framework import generics, status, permissions, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import login, logout
from .models import Usuario, Categoria, Subcategoria, Producto, Pedido, DetallePedido, Comentario, Calificacion, Like
from .serializers import (
    UsuarioSerializer, UsuarioPerfilSerializer, RegistroUsuarioSerializer, LoginSerializer,
    CategoriaSerializer, SubcategoriaSerializer, ProductoSerializer,
    PedidoSerializer, DetallePedidoSerializer, ComentarioSerializer,
    CalificacionSerializer, LikeSerializer, LikeComentarioSerializer, NotificacionSerializer
)
from .cart import Cart
from .utils_pdf import generar_pdf_pedido
from django.http import HttpResponse
from .stats import historial_compras, ventas_por_dia, productos_mas_vendidos, mejores_clientes
from .notificaciones import notificar_usuario
import logging

logger = logging.getLogger(__name__)

from .models import Comentario, LikeComentario, Notificacion
from rest_framework import generics

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
        cart = Cart(request)
        data = [
            {
                'producto_id': item['producto'].id,
                'nombre': item['producto'].nombre,
                'cantidad': item['cantidad'],
                'precio': float(item['precio']),
                'total': float(item['total'])
            } for item in cart
        ]
        logger.info(f"Usuario {request.user.numero} consultó su carrito.")
        return Response({'carrito': data, 'total': float(cart.get_total())})

    def post(self, request):
        producto_id = request.data.get('producto_id')
        cantidad = int(request.data.get('cantidad', 1))
        try:
            Cart(request).add(producto_id, cantidad)
            logger.info(f"Producto {producto_id} añadido al carrito de {request.user.numero}")
            return Response({'success': 'Producto añadido al carrito.'})
        except Exception as e:
            logger.error(f"Error añadiendo producto al carrito: {e}")
            return Response({'error': str(e)}, status=400)

    def delete(self, request):
        producto_id = request.data.get('producto_id')
        Cart(request).remove(producto_id)
        logger.info(f"Producto {producto_id} eliminado del carrito de {request.user.numero}")
        return Response({'success': 'Producto eliminado del carrito.'})

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
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            if not user.esta_activo:
                logger.warning(f"Intento de login de usuario desactivado: {user.numero}")
                return Response({'error': 'Usuario desactivado.'}, status=status.HTTP_403_FORBIDDEN)
            login(request, user)
            logger.info(f"Usuario logueado: {user.numero}")
            return Response(UsuarioSerializer(user).data)
        logger.warning(f"Login fallido: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Logout
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        logger.info(f"Usuario cerró sesión: {request.user.numero}")
        logout(request)
        return Response({'success': 'Sesión cerrada correctamente.'})

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

# Búsqueda avanzada de productos
class BusquedaProductoView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    def get(self, request):
        q = request.query_params.get('q', '')
        categoria = request.query_params.get('categoria')
        subcategoria = request.query_params.get('subcategoria')
        destacados = request.query_params.get('destacados')
        queryset = Producto.objects.filter(activo=True, stock__gt=0)
        if q:
            queryset = queryset.filter(nombre__icontains=q)
        if categoria:
            queryset = queryset.filter(categoria_id=categoria)
        if subcategoria:
            queryset = queryset.filter(subcategoria_id=subcategoria)
        if destacados == '1':
            queryset = queryset.filter(destacado=True)
        logger.info(f"Busqueda avanzada realizada. Query: {q}, Categoria: {categoria}, Subcategoria: {subcategoria}, Destacados: {destacados}")
        return Response(ProductoSerializer(queryset, many=True).data)

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
        if instance.usuario != self.request.user:
            logger.warning(f"Usuario {self.request.user.numero} intentó eliminar producto ajeno #{instance.id}")
            raise PermissionDenied("Solo puedes eliminar tus propios productos.")
        instance.delete()

class PedidoViewSet(viewsets.ModelViewSet):
    serializer_class = PedidoSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Pedido.objects.all()

    def get_queryset(self):
        if getattr(self.request.user, 'es_admin', False):
            return Pedido.objects.all()
        return Pedido.objects.filter(usuario=self.request.user)

    def perform_create(self, serializer):
        if getattr(self.request.user, 'es_admin', False):
            raise PermissionDenied("Solo clientes pueden crear pedidos.")
        serializer.save(usuario=self.request.user)
        logger.info(f"Pedido creado por usuario {self.request.user.numero}")
        # Notificar a todos los admins (puedes mejorar para múltiples admins)
        admin = Usuario.objects.filter(es_admin=True, esta_activo=True).first()
        if admin:
            notificar_usuario('admin', admin.id, {
                'tipo': 'nuevo_pedido',
                'mensaje': f'Nuevo pedido #{serializer.instance.id} realizado por {self.request.user.nombre}.'
            })

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.usuario != self.request.user:
            logger.warning(f"Usuario {self.request.user.numero} intentó editar pedido ajeno #{instance.id}")
            raise PermissionDenied("Solo puedes editar tus propios pedidos.")
        serializer.save()
        # Notificar al cliente si el admin cambia el estado del pedido
        if self.request.user.es_admin:
            notificar_usuario('cliente', instance.usuario.id, {
                'tipo': 'estado_pedido',
                'mensaje': f'El estado de tu pedido #{instance.id} ha cambiado a {serializer.validated_data.get("estado", instance.estado)}.'
            })

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
        serializer.save()

class ComentarioViewSet(viewsets.ModelViewSet):
    serializer_class = ComentarioSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Comentario.objects.all()

    def get_queryset(self):
        return Comentario.objects.filter(producto__activo=True)

    def perform_create(self, serializer):
        comentario = serializer.save(usuario=self.request.user)
        logger.info(f"Comentario creado por usuario {self.request.user.numero}")
        # Notificar al admin de nuevo comentario
        admin = Usuario.objects.filter(es_admin=True, esta_activo=True).first()
        if admin:
            notificar_usuario('admin', admin.id, {
                'tipo': 'nuevo_comentario',
                'mensaje': f'Nuevo comentario en producto #{comentario.producto.id} por {self.request.user.nombre}.'
            })
        # Notificar al dueño del producto
        if comentario.producto.usuario:
            notificar_usuario('cliente', comentario.producto.usuario.id, {
                'tipo': 'nuevo_comentario',
                'mensaje': f'Nuevo comentario en tu producto #{comentario.producto.id} por {self.request.user.nombre}.'
            })

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
        serializer.save(usuario=self.request.user)
        logger.info(f"Calificación creada por usuario {self.request.user.numero}")
        # Notificar al dueño del producto
        if serializer.instance.producto.usuario:
            notificar_usuario('cliente', serializer.instance.producto.usuario.id, {
                'tipo': 'nueva_calificacion',
                'mensaje': f'Nueva calificación en tu producto #{serializer.instance.producto.id} por {self.request.user.nombre}.'
            })

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
        # Notificar al admin de nuevo like
        admin = Usuario.objects.filter(es_admin=True, esta_activo=True).first()
        if admin:
            notificar_usuario('admin', admin.id, {
                'tipo': 'nuevo_like',
                'mensaje': f'Nuevo like en producto #{like.producto.id} por {self.request.user.nombre}.'
            })

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
