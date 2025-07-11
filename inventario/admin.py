from django.contrib import admin
from .models import LogAdmin, Venta, EstadisticaVenta

admin.site.register(LogAdmin)
admin.site.register(Venta)
admin.site.register(EstadisticaVenta)