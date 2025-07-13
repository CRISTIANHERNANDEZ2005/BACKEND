from django.urls import path, include

urlpatterns = [
    path('cliente/', include('tienda.urls_cliente')),
    path('admin/', include('tienda.urls_admin')),
]
