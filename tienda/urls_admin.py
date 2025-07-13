from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views_admin import (
    CategoriaViewSet, SubcategoriaViewSet, ProductoViewSet,
    EstadoVentaViewSet, CompraViewSet, DetalleCompraViewSet,
    ComprasAdminView, AdminStatsView, DestacarProductoView, ReordenarImagenesView, SubirImagenesProductoView,
    HistorialAccionAdminView, AccionesDisponiblesView, ImagenProductoViewSet
)

# =========================
# Rutas RESTful para modelos principales (CRUD)
# =========================
router = DefaultRouter()
router.register(r'categorias', CategoriaViewSet, basename='admin-categorias')
router.register(r'subcategorias', SubcategoriaViewSet, basename='admin-subcategorias')
router.register(r'productos', ProductoViewSet, basename='admin-productos')
router.register(r'estados-venta', EstadoVentaViewSet, basename='admin-estados-venta')
router.register(r'compras', CompraViewSet, basename='admin-compras')
router.register(r'detalles-compra', DetalleCompraViewSet, basename='admin-detalles-compra')
router.register(r'imagenes-producto', ImagenProductoViewSet, basename='admin-imagenes-producto')

# =========================
# Rutas explícitas para acciones especiales de administración
# =========================
urlpatterns = [
    # Gestión y consulta avanzada de compras
    path('compras/', ComprasAdminView.as_view(), name='compras-admin'),
    # Estadísticas globales
    path('stats/', AdminStatsView.as_view(), name='stats-admin'),
    # Destacar productos
    path('productos/<int:pk>/destacar/', DestacarProductoView.as_view(), name='destacar-producto'),
    # Gestión avanzada de imágenes de productos
    path('productos/<int:producto_id>/imagenes/reordenar/', ReordenarImagenesView.as_view(), name='reordenar-imagenes'),
    path('productos/<int:producto_id>/imagenes/subir/', SubirImagenesProductoView.as_view(), name='subir-imagenes-producto'),
    # Historial de acciones y tipos de acciones
    path('acciones/', HistorialAccionAdminView.as_view(), name='acciones-admin'),
    path('acciones/tipos/', AccionesDisponiblesView.as_view(), name='acciones-tipos'),
    # Rutas RESTful
    path('', include(router.urls)),
] 