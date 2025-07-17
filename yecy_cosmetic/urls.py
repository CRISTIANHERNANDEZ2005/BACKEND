from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from django.http import JsonResponse

urlpatterns = [
    path("", lambda request: JsonResponse({"mensaje": "¡Bienvenido a la API de YE&CY COSMETIC!"})),
    path("admin/", admin.site.urls),
    path("api/cliente/", include("tienda.urls_cliente")),
    path("api/admin/", include("tienda.urls_admin")),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Documentar las rutas (puedo ayudarte a generar una documentación tipo OpenAPI/Swagger)