"""
Comando profesional de Django para carga masiva de categorías y productos de cosméticos.
Uso: python manage.py carga_cosmeticos
"""
from django.core.management.base import BaseCommand
from tienda.models import Categoria, Subcategoria, Producto, ImagenProducto
from django.db import transaction

CATEGORIAS = [
    {
        'nombre': 'Cuidado Facial',
        'subcategorias': [
            {
                'nombre': 'Limpieza',
                'productos': [
                    {
                        'nombre': 'Gel Limpiador Suave',
                        'descripcion': 'Gel facial para limpieza profunda sin resecar.',
                        'precio': 49.90,
                        'stock': 50,
                        'imagenes': [
                            {'url_imagen': 'https://cdn.example.com/cosmeticos/gel-limpiador.jpg'},
                        ]
                    },
                    {
                        'nombre': 'Agua Micelar Desmaquillante',
                        'descripcion': 'Desmaquilla y limpia en un solo paso. Apta para piel sensible.',
                        'precio': 39.90,
                        'stock': 40,
                        'imagenes': [
                            {'url_imagen': 'https://cdn.example.com/cosmeticos/agua-micelar.jpg'},
                        ]
                    },
                ]
            },
            {
                'nombre': 'Hidratación',
                'productos': [
                    {
                        'nombre': 'Crema Hidratante Ligera',
                        'descripcion': 'Hidrata intensamente sin sensación grasosa.',
                        'precio': 59.90,
                        'stock': 30,
                        'imagenes': [
                            {'url_imagen': 'https://cdn.example.com/cosmeticos/crema-hidratante.jpg'},
                        ]
                    },
                ]
            }
        ]
    },
    {
        'nombre': 'Maquillaje',
        'subcategorias': [
            {
                'nombre': 'Labios',
                'productos': [
                    {
                        'nombre': 'Labial Mate Rojo',
                        'descripcion': 'Color intenso, larga duración, acabado mate.',
                        'precio': 29.90,
                        'stock': 60,
                        'imagenes': [
                            {'url_imagen': 'https://cdn.example.com/cosmeticos/labial-mate-rojo.jpg'},
                        ]
                    }
                ]
            },
            {
                'nombre': 'Ojos',
                'productos': [
                    {
                        'nombre': 'Máscara de Pestañas Volumen',
                        'descripcion': 'Pestañas más largas y con volumen, resistente al agua.',
                        'precio': 34.90,
                        'stock': 45,
                        'imagenes': [
                            {'url_imagen': 'https://cdn.example.com/cosmeticos/mascara-volumen.jpg'},
                        ]
                    }
                ]
            }
        ]
    }
]

class Command(BaseCommand):
    help = 'Carga masiva profesional de categorías y productos de cosméticos.'

    def handle(self, *args, **options):
        with transaction.atomic():
            for cat_data in CATEGORIAS:
                categoria, _ = Categoria.objects.get_or_create(nombre=cat_data['nombre'])
                for subcat_data in cat_data['subcategorias']:
                    subcategoria, _ = Subcategoria.objects.get_or_create(
                        nombre=subcat_data['nombre'], categoria=categoria)
                    for prod_data in subcat_data['productos']:
                        producto, _ = Producto.objects.get_or_create(
                            subcategoria=subcategoria,
                            nombre=prod_data['nombre'],
                            defaults={
                                'descripcion': prod_data['descripcion'],
                                'precio': prod_data['precio'],
                                'stock': prod_data['stock'],
                                'activo': True,
                            }
                        )
                        for i, img_data in enumerate(prod_data['imagenes']):
                            ImagenProducto.objects.get_or_create(
                                producto=producto,
                                url_imagen=img_data['url_imagen'],
                                orden=i,
                                es_principal=(i==0)
                            )
        self.stdout.write(self.style.SUCCESS('Categorías, subcategorías y productos de cosméticos cargados profesionalmente.'))
