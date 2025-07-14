from rest_framework import serializers
from .models import Usuario, Categoria, Subcategoria, Producto, Pedido, DetallePedido, Comentario, Calificacion, Like, LikeComentario, Notificacion, HistorialAccion, EstadoVenta, Compra, DetalleCompra, ImagenProducto, Carrito, CarritoItem
from django.contrib.auth import authenticate
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

# Serializer personalizado para JWT que usa numero en lugar de username
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'numero'
    
    def validate(self, attrs):
        data = super().validate(attrs)
        data['numero'] = self.user.numero
        data['nombre'] = self.user.nombre
        data['apellido'] = self.user.apellido
        data['es_admin'] = self.user.es_admin
        return data

class UsuarioPerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = (
            'id', 'numero', 'nombre', 'apellido', 'es_admin', 'esta_activo', 'fecha_registro',
            'ultimo_login_exitoso', 'ultimo_ip', 'intentos_fallidos', 'bloqueado_hasta'
        )
        read_only_fields = ('numero', 'es_admin', 'fecha_registro', 'ultimo_login_exitoso', 'ultimo_ip', 'intentos_fallidos', 'bloqueado_hasta')

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = (
            'id', 'numero', 'nombre', 'apellido', 'es_admin', 'esta_activo', 'fecha_registro',
            'ultimo_login_exitoso', 'ultimo_ip', 'intentos_fallidos', 'bloqueado_hasta'
        )

class RegistroUsuarioSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    class Meta:
        model = Usuario
        fields = ('numero', 'nombre', 'apellido', 'password')
    def create(self, validated_data):
        return Usuario.objects.create_user(**validated_data)

class HistorialAccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistorialAccion
        fields = ('id', 'accion', 'detalle', 'fecha', 'ip')

class LoginSerializer(serializers.Serializer):
    numero = serializers.CharField()
    password = serializers.CharField(write_only=True)
    def validate(self, data):
        user = authenticate(numero=data['numero'], password=data['password'])
        if not user:
            raise serializers.ValidationError('Número o contraseña incorrectos.')
        if not user.esta_activo:
            raise serializers.ValidationError('Usuario desactivado.')
        data['user'] = user
        return data

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'

class SubcategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subcategoria
        fields = '__all__'

class ImagenProductoSerializer(serializers.ModelSerializer):
    imagen_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ImagenProducto
        fields = ('id', 'imagen', 'url_imagen', 'imagen_url', 'descripcion', 'orden', 'es_principal')
        read_only_fields = ('imagen_url',)
    
    def get_imagen_url(self, obj):
        """Retorna la URL de la imagen (local o externa)"""
        return obj.get_imagen_url()
    
    def validate(self, data):
        """Validación personalizada para asegurar que se proporcione imagen o URL"""
        imagen = data.get('imagen')
        url_imagen = data.get('url_imagen')
        
        if not imagen and not url_imagen:
            raise serializers.ValidationError("Debe proporcionar una imagen o una URL de imagen.")
        
        if imagen and url_imagen:
            raise serializers.ValidationError("No puede proporcionar tanto imagen como URL. Elija uno de los dos.")
        
        return data

class ProductoSerializer(serializers.ModelSerializer):
    imagenes = ImagenProductoSerializer(many=True, read_only=True)

    class Meta:
        model = Producto
        fields = '__all__'

    def validate(self, data):
        """
        Validación profesional: Un producto debe tener al menos una imagen asociada (local o URL) a través de ImagenProducto.
        Esta validación aplica en la API REST (creación/actualización).
        """
        instance = getattr(self, 'instance', None)
        imagenes = None
        # Si es actualización, usar imágenes actuales
        if instance is not None:
            imagenes = instance.imagenes.all()
        # Si es creación, aún no existen imágenes relacionadas
        request = self.context.get('request')
        if request and request.method in ['PUT', 'PATCH']:
            if imagenes is not None and not imagenes.exists():
                raise serializers.ValidationError("Debe asociar al menos una imagen (local o URL) al producto antes de guardarlo.")
        return data


class CarritoItemProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = ('id', 'nombre', 'precio', 'imagen', 'stock', 'activo')

class CarritoItemSerializer(serializers.ModelSerializer):
    producto = CarritoItemProductoSerializer(read_only=True)
    producto_id = serializers.PrimaryKeyRelatedField(queryset=Producto.objects.all(), source='producto', write_only=True)
    class Meta:
        model = CarritoItem
        fields = ('id', 'producto', 'producto_id', 'cantidad')

class CarritoSerializer(serializers.ModelSerializer):
    items = CarritoItemSerializer(many=True, read_only=True)
    class Meta:
        model = Carrito
        fields = ('id', 'usuario', 'items', 'actualizado')

class PedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pedido
        fields = '__all__'

class DetallePedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetallePedido
        fields = '__all__'

class ComentarioSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source='usuario.nombre', read_only=True)
    respuestas = serializers.SerializerMethodField()
    likes_count = serializers.IntegerField(source='likes.count', read_only=True)
    class Meta:
        model = Comentario
        fields = ['id', 'usuario', 'usuario_nombre', 'producto', 'texto', 'creado', 'activo', 'comentario_padre', 'respuestas', 'likes_count']

    def get_respuestas(self, obj):
        return ComentarioSerializer(obj.respuestas.filter(activo=True), many=True).data

class LikeComentarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = LikeComentario
        fields = ['id', 'usuario', 'comentario', 'creado']

class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = ['id', 'usuario', 'tipo', 'mensaje', 'leida', 'creada', 'eliminada']

class CalificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Calificacion
        fields = '__all__'

class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = '__all__'

class EstadoVentaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstadoVenta
        fields = '__all__'

class DetalleCompraSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    class Meta:
        model = DetalleCompra
        fields = ['id', 'compra', 'producto', 'producto_nombre', 'cantidad', 'precio_unitario']

class CompraSerializer(serializers.ModelSerializer):
    detalles = DetalleCompraSerializer(many=True, read_only=True)
    class Meta:
        model = Compra
        fields = ['id', 'usuario', 'total', 'creado', 'actualizado', 'observaciones', 'activo', 'detalles']
