from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegistroUsuarioView, LoginView, LogoutView,
    CartView, CartClearView,
    CategoriaViewSet, SubcategoriaViewSet, ProductoViewSet,
    PedidoViewSet, DetallePedidoViewSet, ComentarioViewSet,
    CalificacionViewSet, LikeViewSet,
    PerfilUsuarioView, BusquedaProductoView, ComentarioForoView, LikeComentarioView,
    NotificacionListView, NotificacionDeleteView, NotificacionMarkReadView,
    ClienteStatsView, AdminStatsView
)

router = DefaultRouter()
router.register(r'categorias', CategoriaViewSet)
router.register(r'subcategorias', SubcategoriaViewSet)
router.register(r'productos', ProductoViewSet)
router.register(r'pedidos', PedidoViewSet)
router.register(r'detalles-pedido', DetallePedidoViewSet)
router.register(r'comentarios', ComentarioViewSet)
router.register(r'calificaciones', CalificacionViewSet)
router.register(r'likes', LikeViewSet)

urlpatterns = [
    path('registro/', RegistroUsuarioView.as_view(), name='registro'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('perfil/', PerfilUsuarioView.as_view(), name='perfil-usuario'),
    path('buscar/', BusquedaProductoView.as_view(), name='buscar-productos'),
    path('comentarios/', ComentarioForoView.as_view(), name='comentarios-foro'),
    path('comentarios/<int:comentario_id>/like/', LikeComentarioView.as_view(), name='like-comentario'),
    path('notificaciones/', NotificacionListView.as_view(), name='notificaciones-lista'),
    path('notificaciones/<int:pk>/eliminar/', NotificacionDeleteView.as_view(), name='notificacion-eliminar'),
    path('notificaciones/<int:pk>/leer/', NotificacionMarkReadView.as_view(), name='notificacion-leer'),
    path('carrito/', CartView.as_view(), name='carrito'),
    path('carrito/limpiar/', CartClearView.as_view(), name='carrito-limpiar'),
    path('stats/cliente/', ClienteStatsView.as_view(), name='stats-cliente'),
    path('stats/admin/', AdminStatsView.as_view(), name='stats-admin'),
    path('', include(router.urls)),
]
