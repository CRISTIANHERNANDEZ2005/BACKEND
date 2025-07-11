from django.db import models
from tienda.models import Usuario, Producto, Pedido
from django.utils import timezone

class LogAdmin(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    accion = models.CharField(max_length=255)
    fecha = models.DateTimeField(default=timezone.now)


    def __str__(self):
        return f"{self.usuario} - {self.accion} ({self.fecha})"

class Venta(models.Model):
    pedido = models.OneToOneField(Pedido, on_delete=models.CASCADE, related_name='venta')
    estado = models.CharField(max_length=20, choices=[('pendiente','Pendiente'),('completada','Completada'),('cancelada','Cancelada')], default='pendiente')
    fecha = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Venta de {self.pedido.usuario} - Estado: {self.estado}"

class EstadisticaVenta(models.Model):
    fecha = models.DateField()
    total_ventas = models.PositiveIntegerField(default=0)
    total_ingresos = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.fecha}: {self.total_ventas} ventas, ${self.total_ingresos}"
