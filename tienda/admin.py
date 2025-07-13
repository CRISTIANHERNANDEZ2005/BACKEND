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
    fields = ('imagen', 'url_imagen', 'descripcion', 'orden', 'es_principal')
    readonly_fields = ('get_imagen_url',)
    
    def get_imagen_url(self, obj):
        if obj:
            return obj.get_imagen_url()
        return "N/A"
    get_imagen_url.short_description = "URL de imagen"

class ImagenProductoAdmin(admin.ModelAdmin):
    list_display = ('producto', 'get_imagen_preview', 'descripcion', 'orden', 'es_principal')
    list_filter = ('es_principal', 'producto__subcategoria')
    search_fields = ('producto__nombre', 'descripcion')
    ordering = ('producto__nombre', 'orden')
    readonly_fields = ('get_imagen_url',)
    
    def get_imagen_preview(self, obj):
        if obj.imagen:
            return f"<img src='{obj.imagen.url}' width='50' height='50' style='object-fit: cover;' />"
        elif obj.url_imagen:
            return f"<a href='{obj.url_imagen}' target='_blank'>Ver imagen externa</a>"
        return "Sin imagen"
    get_imagen_preview.short_description = "Vista previa"
    get_imagen_preview.allow_tags = True
    
    def get_imagen_url(self, obj):
        return obj.get_imagen_url()
    get_imagen_url.short_description = "URL de imagen"

class ProductoAdmin(admin.ModelAdmin):
    inlines = [ImagenProductoInline]
    list_display = ('nombre', 'subcategoria', 'precio', 'stock', 'destacado', 'activo', 'get_imagen_principal')
    list_filter = ('subcategoria', 'destacado', 'activo')
    search_fields = ('nombre',)
    readonly_fields = ('fecha_creacion',)
    
    def get_imagen_principal(self, obj):
        imagen_principal = obj.imagenes.filter(es_principal=True).first()
        if imagen_principal:
            if imagen_principal.imagen:
                return f"<img src='{imagen_principal.imagen.url}' width='30' height='30' style='object-fit: cover;' />"
            elif imagen_principal.url_imagen:
                return f"<a href='{imagen_principal.url_imagen}' target='_blank'>🔗</a>"
        return "Sin imagen"
    get_imagen_principal.short_description = "Imagen principal"
    get_imagen_principal.allow_tags = True

admin.site.register(Producto, ProductoAdmin)
admin.site.register(ImagenProducto, ImagenProductoAdmin)
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
