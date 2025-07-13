from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from .views_cliente import (
    RegistroUsuarioView, LoginView, LogoutView,
    CartView, CartClearView, CarritoMigrarView, ComprarView,
    PerfilUsuarioView, BusquedaProductoView, ProductosDestacadosView,
    ComentarioForoView, LikeComentarioView, NotificacionListView, NotificacionDeleteView, NotificacionMarkReadView,
    ComprasUsuarioView, ClienteStatsView,
    PedidoViewSet, DetallePedidoViewSet, ComentarioViewSet, CalificacionViewSet, LikeViewSet,
    ImagenesProductoView,
    RecuperarPasswordView, ResetPasswordView, CambiarPasswordView,
    HistorialAccionClienteView,
    CategoriaPublicaListView, SubcategoriaPublicaListView
)

router = DefaultRouter()
router.register(r'pedidos', PedidoViewSet, basename='cliente-pedidos')
router.register(r'detalles-pedido', DetallePedidoViewSet, basename='cliente-detalles-pedido')
router.register(r'comentarios', ComentarioViewSet, basename='cliente-comentarios')
router.register(r'calificaciones', CalificacionViewSet, basename='cliente-calificaciones')
router.register(r'likes', LikeViewSet, basename='cliente-likes')

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('registro/', RegistroUsuarioView.as_view(), name='registro'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('auth/recuperar/', RecuperarPasswordView.as_view(), name='recuperar-password'),
    path('auth/reset/', ResetPasswordView.as_view(), name='reset-password'),
    path('auth/cambiar-password/', CambiarPasswordView.as_view(), name='cambiar-password'),
    path('acciones/', HistorialAccionClienteView.as_view(), name='acciones-cliente'),
    path('perfil/', PerfilUsuarioView.as_view(), name='perfil-usuario'),
    path('buscar/', BusquedaProductoView.as_view(), name='buscar-productos'),
    path('productos/destacados/', ProductosDestacadosView.as_view(), name='productos-destacados'),
    path('comentarios/foro/', ComentarioForoView.as_view(), name='comentarios-foro'),
    path('comentarios/<int:comentario_id>/like/', LikeComentarioView.as_view(), name='like-comentario'),
    path('notificaciones/', NotificacionListView.as_view(), name='notificaciones-lista'),
    path('notificaciones/<int:pk>/eliminar/', NotificacionDeleteView.as_view(), name='notificacion-eliminar'),
    path('notificaciones/<int:pk>/leer/', NotificacionMarkReadView.as_view(), name='notificacion-leer'),
    path('carrito/', CartView.as_view(), name='carrito'),
    path('carrito/limpiar/', CartClearView.as_view(), name='carrito-limpiar'),
    path('carrito/migrar/', CarritoMigrarView.as_view(), name='carrito-migrar'),
    path('comprar/', ComprarView.as_view(), name='comprar'),
    path('compras/', ComprasUsuarioView.as_view(), name='compras-usuario'),
    path('stats/', ClienteStatsView.as_view(), name='stats-cliente'),
    path('productos/<int:producto_id>/imagenes/', ImagenesProductoView.as_view(), name='imagenes-producto'),
    path('', include(router.urls)),
]

urlpatterns += [
    path('categorias/', CategoriaPublicaListView.as_view(), name='categorias-publicas'),
    path('categorias/<int:categoria_id>/subcategorias/', SubcategoriaPublicaListView.as_view(), name='subcategorias-publicas'),
] 