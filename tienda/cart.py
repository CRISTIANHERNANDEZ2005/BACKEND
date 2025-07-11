from decimal import Decimal
from django.conf import settings
from tienda.models import Producto
import logging

logger = logging.getLogger(__name__)

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, producto_id, cantidad=1, override_cantidad=False):
        producto = Producto.objects.filter(id=producto_id, activo=True, stock__gte=cantidad).first()
        if not producto:
            logger.warning(f"Intento de añadir producto inválido o sin stock: {producto_id}")
            raise ValueError("Producto no disponible o sin stock")
        producto_id = str(producto_id)
        if producto_id not in self.cart:
            self.cart[producto_id] = {'cantidad': 0, 'precio': str(producto.precio)}
        if override_cantidad:
            self.cart[producto_id]['cantidad'] = cantidad
        else:
            self.cart[producto_id]['cantidad'] += cantidad
        if self.cart[producto_id]['cantidad'] > producto.stock:
            logger.error(f"Cantidad solicitada supera stock: {producto_id}")
            self.cart[producto_id]['cantidad'] = producto.stock
        self.save()

    def save(self):
        self.session[settings.CART_SESSION_ID] = self.cart
        self.session.modified = True

    def remove(self, producto_id):
        producto_id = str(producto_id)
        if producto_id in self.cart:
            del self.cart[producto_id]
            self.save()

    def clear(self):
        self.session[settings.CART_SESSION_ID] = {}
        self.session.modified = True

    def __iter__(self):
        productos_ids = self.cart.keys()
        productos = Producto.objects.filter(id__in=productos_ids)
        for producto in productos:
            item = self.cart[str(producto.id)]
            item['producto'] = producto
            item['precio'] = Decimal(item['precio'])
            item['total'] = item['precio'] * item['cantidad']
            yield item

    def __len__(self):
        return sum(item['cantidad'] for item in self.cart.values())

    def get_total(self):
        return sum(Decimal(item['precio']) * item['cantidad'] for item in self.cart.values())
