from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone

# -----------------------------
# MANAGER DE USUARIO PERSONALIZADO
# -----------------------------
class UsuarioManager(BaseUserManager):
    def create_user(self, numero, nombre, apellido, password=None, **extra_fields):
        if not numero:
            raise ValueError('El número de teléfono es obligatorio')
        if len(str(numero)) != 10:
            raise ValueError('El número debe tener 10 dígitos')
        user = self.model(
            numero=numero,
            nombre=nombre,
            apellido=apellido,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, numero, nombre, apellido, password=None, **extra_fields):
        extra_fields.setdefault('es_admin', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(numero, nombre, apellido, password, **extra_fields)

# -----------------------------
# MODELO DE USUARIO PERSONALIZADO
# -----------------------------
class Usuario(AbstractBaseUser, PermissionsMixin):
    numero = models.CharField(max_length=10, unique=True, verbose_name="Número de teléfono")
    nombre = models.CharField(max_length=30)
    apellido = models.CharField(max_length=30)
    es_admin = models.BooleanField(default=False)
    esta_activo = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    fecha_registro = models.DateTimeField(default=timezone.now)
    # Seguridad y auditoría
    intentos_fallidos = models.PositiveIntegerField(default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)
    ultimo_login_exitoso = models.DateTimeField(null=True, blank=True)
    ultimo_ip = models.CharField(max_length=45, blank=True, null=True)

    USERNAME_FIELD = 'numero'
    REQUIRED_FIELDS = ['nombre', 'apellido']

    objects = UsuarioManager()

    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.numero})"

class HistorialAccion(models.Model):
    usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE, related_name='historial_acciones')
    accion = models.CharField(max_length=100)
    detalle = models.TextField(blank=True, null=True)
    fecha = models.DateTimeField(default=timezone.now)
    ip = models.CharField(max_length=45, blank=True, null=True)

    def __str__(self):
        return f"{self.usuario} - {self.accion} - {self.fecha.strftime('%Y-%m-%d %H:%M:%S')}"

# -----------------------------
# MODELOS DE CATEGORÍA Y PRODUCTOS
# -----------------------------
class Categoria(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    activa = models.BooleanField(default=True, db_index=True)  # Índice para búsquedas frecuentes

    def __str__(self):
        return self.nombre

class Subcategoria(models.Model):
    categoria = models.ForeignKey(Categoria, related_name='subcategorias', on_delete=models.CASCADE, db_index=True)
    nombre = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True, null=True)
    activa = models.BooleanField(default=True, db_index=True)

    def __str__(self):
        return f"{self.nombre} ({self.categoria.nombre})"

class Producto(models.Model):
    subcategoria = models.ForeignKey(Subcategoria, related_name='productos', on_delete=models.CASCADE, db_index=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    imagen = models.ImageField(upload_to='productos/', null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    destacado = models.BooleanField(default=False, db_index=True)
    activo = models.BooleanField(default=True, db_index=True)
    fecha_creacion = models.DateTimeField(default=timezone.now, db_index=True)

    def clean(self):
        """
        Validación profesional: Un producto debe tener al menos una imagen asociada (local o URL) a través de ImagenProducto.
        Esta validación se aplica en el admin y en operaciones programáticas (no en el serializer DRF).
        """
        from django.core.exceptions import ValidationError
        super().clean()
        # Solo validar si el producto ya tiene PK (para evitar error en creación inicial)
        if self.pk:
            if not self.imagenes.exists():
                raise ValidationError("Debe asociar al menos una imagen (local o URL) al producto antes de guardarlo.")

    def __str__(self):
        return self.nombre

class ImagenProducto(models.Model):
    producto = models.ForeignKey(Producto, related_name='imagenes', on_delete=models.CASCADE)
    imagen = models.ImageField(upload_to='productos/imagenes/', null=True, blank=True)
    url_imagen = models.URLField(max_length=500, blank=True, null=True, help_text="URL de imagen externa")
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    orden = models.PositiveIntegerField(default=0)
    es_principal = models.BooleanField(default=False, help_text="Indica si es la imagen principal del producto")

    class Meta:
        ordering = ['orden', 'id']

    def clean(self):
        """Validación personalizada para asegurar que se proporcione imagen o URL"""
        from django.core.exceptions import ValidationError
        if not self.imagen and not self.url_imagen:
            raise ValidationError("Debe proporcionar una imagen o una URL de imagen.")
        if self.imagen and self.url_imagen:
            raise ValidationError("No puede proporcionar tanto imagen como URL. Elija uno de los dos.")

    def save(self, *args, **kwargs):
        """Asegura que solo una imagen sea principal por producto"""
        if self.es_principal:
            # Desmarcar otras imágenes principales del mismo producto
            ImagenProducto.objects.filter(producto=self.producto, es_principal=True).exclude(pk=self.pk).update(es_principal=False)
        super().save(*args, **kwargs)

    def get_imagen_url(self):
        """Retorna la URL de la imagen (local o externa)"""
        if self.imagen:
            return self.imagen.url
        return self.url_imagen

    def __str__(self):
        return f"Imagen de {self.producto.nombre} ({self.id})"

# -----------------------------
# MODELOS DE CARRITO PERSISTENTE
# -----------------------------

class Carrito(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='carrito')
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Carrito de {self.usuario.numero}"

class CarritoItem(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('carrito', 'producto')

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} ({self.carrito.usuario.numero})"

# -----------------------------
# MODELOS DE PEDIDO Y DETALLE
# -----------------------------
class EstadoVenta(models.Model):
    nombre = models.CharField(max_length=30, unique=True)
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)
    def __str__(self):
        return self.nombre

class Pedido(models.Model):
    usuario = models.ForeignKey('Usuario', related_name='pedidos', on_delete=models.CASCADE)
    estado = models.ForeignKey('EstadoVenta', related_name='pedidos', on_delete=models.PROTECT)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    creado = models.DateTimeField(default=timezone.now)
    actualizado = models.DateTimeField(auto_now=True)
    pdf = models.FileField(upload_to='pedidos/pdf/', null=True, blank=True)
    creado_por = models.ForeignKey('Usuario', null=True, blank=True, related_name='ventas_registradas', on_delete=models.SET_NULL)
    metodo_pago = models.CharField(max_length=30, default='contraentrega')
    activo = models.BooleanField(default=True)
    def __str__(self):
        return f"Pedido #{self.id} de {self.usuario}"

class Compra(models.Model):
    usuario = models.ForeignKey('Usuario', related_name='compras_registradas', on_delete=models.SET_NULL, null=True, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    creado = models.DateTimeField(default=timezone.now)
    actualizado = models.DateTimeField(auto_now=True)
    observaciones = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    def __str__(self):
        return f"Compra #{self.id}"

class DetalleCompra(models.Model):
    compra = models.ForeignKey('Compra', related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey('Producto', on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} (Compra #{self.compra.id})"

class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"

# -----------------------------
# MODELOS DE INTERACCIÓN: COMENTARIO, CALIFICACIÓN, LIKE
# -----------------------------
class Comentario(models.Model):
    usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, related_name='comentarios', on_delete=models.CASCADE)
    texto = models.TextField()
    creado = models.DateTimeField(default=timezone.now)
    activo = models.BooleanField(default=True)
    comentario_padre = models.ForeignKey('self', null=True, blank=True, related_name='respuestas', on_delete=models.CASCADE)

    def __str__(self):
        return f"Comentario de {self.usuario} en {self.producto}"

class LikeComentario(models.Model):
    usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE)
    comentario = models.ForeignKey(Comentario, related_name='likes', on_delete=models.CASCADE)
    creado = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('usuario', 'comentario')

    def __str__(self):
        return f"Like de {self.usuario} en comentario {self.comentario.id}"

class Notificacion(models.Model):
    usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE, related_name='notificaciones')
    tipo = models.CharField(max_length=30)
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    creada = models.DateTimeField(default=timezone.now)
    eliminada = models.BooleanField(default=False)

    def __str__(self):
        return f"Notificación para {self.usuario}: {self.mensaje[:30]}..."

class Calificacion(models.Model):
    usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, related_name='calificaciones', on_delete=models.CASCADE)
    valor = models.PositiveSmallIntegerField(default=5)
    creado = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('usuario', 'producto')

    def __str__(self):
        return f"{self.valor}⭐ de {self.usuario} en {self.producto.nombre}"

class Like(models.Model):
    usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, related_name='likes', on_delete=models.CASCADE)
    creado = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('usuario', 'producto')

    def __str__(self):
        return f"Like de {self.usuario} en {self.producto.nombre}"
