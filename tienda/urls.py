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
    ClienteStatsView, AdminStatsView,
    RecuperarPasswordView, ResetPasswordView, CambiarPasswordView,
    HistorialAccionClienteView, HistorialAccionAdminView, AccionesDisponiblesView,
    ProductosDestacadosView, DestacarProductoView, CarritoMigrarView, ComprarView,
    ComprasUsuarioView, ComprasAdminView, 
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
    path('auth/recuperar/', RecuperarPasswordView.as_view(), name='recuperar-password'),
    path('auth/reset/', ResetPasswordView.as_view(), name='reset-password'),
    path('auth/cambiar-password/', CambiarPasswordView.as_view(), name='cambiar-password'),
    path('acciones/cliente/', HistorialAccionClienteView.as_view(), name='acciones-cliente'),
    path('acciones/admin/', HistorialAccionAdminView.as_view(), name='acciones-admin'),
    path('acciones/tipos/', AccionesDisponiblesView.as_view(), name='acciones-tipos'),
    path('perfil/', PerfilUsuarioView.as_view(), name='perfil-usuario'),
    path('buscar/', BusquedaProductoView.as_view(), name='buscar-productos'),
    path('productos/destacados/', ProductosDestacadosView.as_view(), name='productos-destacados'),
    path('productos/<int:pk>/destacar/', DestacarProductoView.as_view(), name='destacar-producto'),
    path('comentarios/', ComentarioForoView.as_view(), name='comentarios-foro'),
    path('comentarios/<int:comentario_id>/like/', LikeComentarioView.as_view(), name='like-comentario'),
    path('notificaciones/', NotificacionListView.as_view(), name='notificaciones-lista'),
    path('notificaciones/<int:pk>/eliminar/', NotificacionDeleteView.as_view(), name='notificacion-eliminar'),
    path('notificaciones/<int:pk>/leer/', NotificacionMarkReadView.as_view(), name='notificacion-leer'),
    path('carrito/', CartView.as_view(), name='carrito'),
    path('carrito/limpiar/', CartClearView.as_view(), name='carrito-limpiar'),
    path('carrito/migrar/', CarritoMigrarView.as_view(), name='carrito-migrar'),
    path('comprar/', ComprarView.as_view(), name='comprar'),
    path('compras/', ComprasUsuarioView.as_view(), name='compras-usuario'),
    path('compras/admin/', ComprasAdminView.as_view(), name='compras-admin'),
    path('stats/cliente/', ClienteStatsView.as_view(), name='stats-cliente'),
    path('stats/admin/', AdminStatsView.as_view(), name='stats-admin'),
    path('', include(router.urls)),
]
