from django.contrib import admin
from .models import Usuario, Categoria, Subcategoria, Producto, Pedido, DetallePedido, Comentario, Calificacion, Like, ImagenProducto, Carrito, CarritoItem, EstadoVenta, Compra, DetalleCompra
from django.contrib.auth.admin import UserAdmin

class UsuarioAdmin(UserAdmin):
    model = Usuario
    list_display = ('numero', 'nombre', 'apellido', 'es_admin', 'esta_activo', 'is_staff')
    list_filter = ('es_admin', 'esta_activo', 'is_staff')
    fieldsets = (
        (None, {'fields': ('numero', 'password')}),
        ('Información personal', {'fields': ('nombre', 'apellido')}),
        ('Permisos', {'fields': ('es_admin', 'esta_activo', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas', {'fields': ('last_login', 'fecha_registro')})
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('numero', 'nombre', 'apellido', 'password1', 'password2', 'es_admin', 'esta_activo', 'is_staff')
        }),
    )
    search_fields = ('numero', 'nombre', 'apellido')
    ordering = ('numero',)
    filter_horizontal = ('groups', 'user_permissions',)

admin.site.register(Usuario, UsuarioAdmin)
admin.site.register(Categoria)
admin.site.register(Subcategoria)
class ImagenProductoInline(admin.StackedInline):
    model = ImagenProducto
    extra = 1

class ProductoAdmin(admin.ModelAdmin):
    inlines = [ImagenProductoInline]
    list_display = ('nombre', 'subcategoria', 'precio', 'stock', 'destacado', 'activo')
    list_filter = ('subcategoria', 'destacado', 'activo')
    search_fields = ('nombre',)

admin.site.register(Producto, ProductoAdmin)
admin.site.register(Pedido)
admin.site.register(DetallePedido)
admin.site.register(Comentario)
admin.site.register(Calificacion)
admin.site.register(Like)
admin.site.register(EstadoVenta)
admin.site.register(Compra)
admin.site.register(DetalleCompra)

class CarritoItemInline(admin.TabularInline):
    model = CarritoItem
    extra = 0

class CarritoAdmin(admin.ModelAdmin):
    inlines = [CarritoItemInline]
    list_display = ('usuario', 'actualizado')
    search_fields = ('usuario__numero',)

admin.site.register(Carrito, CarritoAdmin)
