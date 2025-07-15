"""
Middleware personalizado para manejar CSRF en desarrollo
"""

from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

class CSRFMiddleware(MiddlewareMixin):
    """
    Middleware que deshabilita CSRF para API en desarrollo, pero nunca afecta rutas WebSocket.
    """
    def process_request(self, request):
        # Excluir WebSocket: nunca tocar rutas que empiecen por /api/ws/
        if request.path.startswith('/api/ws/'):
            return None
        # Permitir todos los métodos seguros (GET, HEAD, OPTIONS) sin CSRF en /api/
        if request.path.startswith('/api/'):
            if request.method in ('GET', 'HEAD', 'OPTIONS'):
                setattr(request, '_dont_enforce_csrf_checks', True)
            # Para POST/PUT/PATCH/DELETE siempre se exige CSRF para evitar problemas al pasar a producción.
        return None 