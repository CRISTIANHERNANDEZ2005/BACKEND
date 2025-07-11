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

    USERNAME_FIELD = 'numero'
    REQUIRED_FIELDS = ['nombre', 'apellido']

    objects = UsuarioManager()

    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.numero})"

# -----------------------------
# MODELOS DE CATEGORÍA Y PRODUCTOS
# -----------------------------
class Categoria(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

class Subcategoria(models.Model):
    categoria = models.ForeignKey(Categoria, related_name='subcategorias', on_delete=models.CASCADE)
    nombre = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True, null=True)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} ({self.categoria.nombre})"

class Producto(models.Model):
    subcategoria = models.ForeignKey(Subcategoria, related_name='productos', on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    imagen = models.ImageField(upload_to='productos/', null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    destacado = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.nombre

# -----------------------------
# MODELOS DE PEDIDO Y DETALLE
# -----------------------------
class Pedido(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    ]
    usuario = models.ForeignKey('Usuario', related_name='pedidos', on_delete=models.CASCADE)
    estado = models.CharField(max_length=10, choices=ESTADOS, default='pendiente')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    creado = models.DateTimeField(default=timezone.now)
    actualizado = models.DateTimeField(auto_now=True)
    pdf = models.FileField(upload_to='pedidos/pdf/', null=True, blank=True)

    def __str__(self):
        return f"Pedido #{self.id} de {self.usuario}"

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
