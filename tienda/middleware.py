"""
Middleware personalizado para manejar CSRF en desarrollo
"""

from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

class CSRFMiddleware(MiddlewareMixin):
    """
    Middleware que deshabilita CSRF para API en desarrollo
    """
    
    def process_request(self, request):
        # Permitir todos los métodos seguros (GET, HEAD, OPTIONS) sin CSRF en /api/
        if request.path.startswith('/api/'):
            if request.method in ('GET', 'HEAD', 'OPTIONS'):
                setattr(request, '_dont_enforce_csrf_checks', True)
            # Tanto en desarrollo como en producción, solo los métodos seguros (GET, HEAD, OPTIONS) están exentos de CSRF en /api/.
            # Para POST/PUT/PATCH/DELETE siempre se exige CSRF para evitar problemas al pasar a producción.
            # Si necesitas desactivar CSRF para pruebas, hazlo explícitamente y temporalmente.
        return None 