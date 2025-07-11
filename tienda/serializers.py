from rest_framework import serializers
from .models import Usuario, Categoria, Subcategoria, Producto, Pedido, DetallePedido, Comentario, Calificacion, Like, LikeComentario, Notificacion
from django.contrib.auth import authenticate

class UsuarioPerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ('id', 'numero', 'nombre', 'apellido', 'es_admin', 'esta_activo', 'fecha_registro')
        read_only_fields = ('numero', 'es_admin', 'fecha_registro')

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ('id', 'numero', 'nombre', 'apellido', 'es_admin', 'esta_activo', 'fecha_registro')

class RegistroUsuarioSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    class Meta:
        model = Usuario
        fields = ('numero', 'nombre', 'apellido', 'password')
    def create(self, validated_data):
        return Usuario.objects.create_user(**validated_data)

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

class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = '__all__'

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
