#!/usr/bin/env python3
"""
API Health Check Tool para YE&CY COSMETIC
==========================================

Este script realiza un testing completo de la API de Django para verificar
que todos los endpoints estén funcionando correctamente antes de pasar a producción.

Uso:
    python test_api_health.py [--user=usuario] [--pass=contraseña] [--admin] [--verbose]

Variables de entorno:
    API_USER: Usuario para autenticación
    API_PASS: Contraseña para autenticación
    API_BASE_URL: URL base de la API (default: http://127.0.0.1:8000/)
    API_ADMIN_USER: Usuario admin para testing
    API_ADMIN_PASS: Contraseña admin para testing
"""

import requests
import sys
import os
import argparse
import json
import time
import random
import string
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

# Configuración por defecto
DEFAULT_BASE_URL = "http://127.0.0.1:8000/"
DEFAULT_TIMEOUT = 10

class APITester:
    def __init__(self, base_url: str, timeout: int = DEFAULT_TIMEOUT, verbose: bool = False):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.verbose = verbose
        self.session = requests.Session()
        self.results = []
        self.token = None
        self.admin_token = None
        
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def test_endpoint(self, name: str, path: str, method: str = "GET", 
                     data: Optional[Dict] = None, token: Optional[str] = None,
                     expected_status: int = 200, validate_response: bool = True) -> bool:
        """Testea un endpoint específico"""
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = {"Content-Type": "application/json"}
        
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        try:
            if method.upper() == "POST":
                response = self.session.post(url, json=data, headers=headers, timeout=self.timeout)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, headers=headers, timeout=self.timeout)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=headers, timeout=self.timeout)
            else:
                response = self.session.get(url, headers=headers, timeout=self.timeout)
                
            success = response.status_code == expected_status
            
            if success:
                self.log(f"✅ {name} ({method} {url}) - Status: {response.status_code}", "SUCCESS")
                if self.verbose and response.content:
                    try:
                        response_data = response.json()
                        self.log(f"   Response: {json.dumps(response_data, indent=2, ensure_ascii=False)}", "DEBUG")
                    except:
                        self.log(f"   Response: {response.text[:200]}...", "DEBUG")
            else:
                self.log(f"❌ {name} ({method} {url}) - Status: {response.status_code}", "ERROR")
                if self.verbose:
                    try:
                        error_data = response.json()
                        self.log(f"   Error: {json.dumps(error_data, indent=2, ensure_ascii=False)}", "DEBUG")
                    except:
                        self.log(f"   Error: {response.text[:200]}...", "DEBUG")
                        
            self.results.append({
                "name": name,
                "url": url,
                "method": method,
                "status_code": response.status_code,
                "expected_status": expected_status,
                "success": success,
                "response_time": response.elapsed.total_seconds()
            })
            
            return success
            
        except requests.exceptions.Timeout:
            self.log(f"⏰ {name} ({method} {url}) - Timeout", "ERROR")
            self.results.append({
                "name": name,
                "url": url,
                "method": method,
                "status_code": None,
                "expected_status": expected_status,
                "success": False,
                "error": "Timeout"
            })
            return False
        except Exception as e:
            self.log(f"💥 {name} ({method} {url}) - Exception: {e}", "ERROR")
            self.results.append({
                "name": name,
                "url": url,
                "method": method,
                "status_code": None,
                "expected_status": expected_status,
                "success": False,
                "error": str(e)
            })
            return False

    def get_jwt_token(self, username: str, password: str, endpoint: str = "api/cliente/token/") -> Optional[str]:
        """Obtiene un token JWT para autenticación"""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self.session.post(url, json={
                "numero": username,  # Usar numero en lugar de username
                "password": password
            }, timeout=self.timeout)
            
            if response.status_code == 200:
                token_data = response.json()
                if "access" in token_data:
                    self.log(f"✅ Token JWT obtenido para {username}", "SUCCESS")
                    return token_data["access"]
                else:
                    self.log(f"❌ Respuesta de token inválida: {token_data}", "ERROR")
                    return None
            else:
                self.log(f"❌ Error al obtener token: {response.status_code}", "ERROR")
                if self.verbose:
                    self.log(f"   Response: {response.text}", "DEBUG")
                return None
        except Exception as e:
            self.log(f"💥 Error al obtener token: {e}", "ERROR")
            return None

    def test_public_endpoints(self) -> bool:
        """Testea endpoints públicos"""
        self.log("🔍 Testing endpoints públicos...", "INFO")
        
        public_endpoints = [
            ("API Root", "", "GET", None, None, 200),
            ("Productos Destacados", "api/cliente/productos/destacados/", "GET", None, None, 200),
            ("Categorías Públicas", "api/cliente/categorias/", "GET", None, None, 200),
            ("Token Verify (sin token)", "api/cliente/token/verify/", "POST", {"token": "invalid"}, None, 401),
        ]
        
        all_success = True
        for name, path, method, data, token, expected_status in public_endpoints:
            if not self.test_endpoint(name, path, method, data, token, expected_status):
                all_success = False
                
        return all_success

    def test_authentication(self, username: str, password: str) -> bool:
        """Testea el sistema de autenticación"""
        self.log("🔐 Testing autenticación...", "INFO")
        
        # Usar credenciales proporcionadas para testing
        test_numero = username or f"555{random.randint(1000000, 9999999)}"
        test_password = password or "testpass123"
        
        auth_endpoints = [
            ("Login con Credenciales", "api/cliente/login/", "POST", {
                "numero": test_numero,
                "password": test_password
            }, None, 200),
            ("Login Fallido", "api/cliente/login/", "POST", {
                "numero": "9999999999",
                "password": "wrongpass"
            }, None, 400),
        ]
        
        all_success = True
        for name, path, method, data, token, expected_status in auth_endpoints:
            if not self.test_endpoint(name, path, method, data, token, expected_status):
                all_success = False
                
        return all_success

    def test_protected_endpoints(self, token: str) -> bool:
        """Testea endpoints que requieren autenticación"""
        self.log("🔒 Testing endpoints protegidos...", "INFO")
        
        protected_endpoints = [
            ("Perfil de Usuario", "api/cliente/perfil/", "GET", None, token, 200),
            ("Carrito", "api/cliente/carrito/", "GET", None, token, 200),
            ("Añadir al Carrito", "api/cliente/carrito/", "POST", {
                "producto_id": 1,
                "cantidad": 1
            }, token, 200),
            ("Limpiar Carrito", "api/cliente/carrito/limpiar/", "POST", None, token, 200),
            ("Compras del Usuario", "api/cliente/compras/", "GET", None, token, 200),
            ("Stats del Cliente", "api/cliente/stats/", "GET", None, token, 200),
            ("Notificaciones", "api/cliente/notificaciones/", "GET", None, token, 200),
            ("Historial de Acciones", "api/cliente/acciones/", "GET", None, token, 200),
        ]
        
        all_success = True
        for name, path, method, data, token, expected_status in protected_endpoints:
            if not self.test_endpoint(name, path, method, data, token, expected_status):
                all_success = False
                
        return all_success

    def test_admin_endpoints(self, admin_token: str) -> bool:
        """Testea endpoints de administración"""
        self.log("👑 Testing endpoints de administración...", "INFO")
        
        admin_endpoints = [
            ("Stats de Admin", "api/admin/stats/", "GET", None, admin_token, 200),
            ("Compras Admin", "api/admin/compras/", "GET", None, admin_token, 200),
            ("Categorías Admin", "api/admin/categorias/", "GET", None, admin_token, 200),
            ("Productos Admin", "api/admin/productos/", "GET", None, admin_token, 200),
            ("Estados de Venta", "api/admin/estados-venta/", "GET", None, admin_token, 200),
        ]
        
        all_success = True
        for name, path, method, data, token, expected_status in admin_endpoints:
            if not self.test_endpoint(name, path, method, data, token, expected_status):
                all_success = False
                
        return all_success

    def test_error_handling(self) -> bool:
        """Testea el manejo de errores"""
        self.log("⚠️ Testing manejo de errores...", "INFO")
        
        error_endpoints = [
            ("Endpoint No Existente", "api/cliente/no-existe/", "GET", None, None, 404),
            ("Método No Permitido", "api/cliente/productos/destacados/", "POST", {}, None, 405),
            ("Acceso No Autorizado", "api/cliente/perfil/", "GET", None, None, 401),
        ]
        
        all_success = True
        for name, path, method, data, token, expected_status in error_endpoints:
            if not self.test_endpoint(name, path, method, data, token, expected_status):
                all_success = False
                
        return all_success

    def test_performance(self) -> bool:
        """Testea el rendimiento básico"""
        self.log("⚡ Testing rendimiento...", "INFO")
        
        # Test de respuesta rápida
        start_time = time.time()
        success = self.test_endpoint("Performance Test", "api/cliente/productos/destacados/", "GET", None, None, 200)
        response_time = time.time() - start_time
        
        if success and response_time < 2.0:
            self.log(f"✅ Performance OK: {response_time:.2f}s", "SUCCESS")
            return True
        else:
            self.log(f"❌ Performance lenta: {response_time:.2f}s", "ERROR")
            return False

    def generate_report(self) -> Dict[str, Any]:
        """Genera un reporte completo de los tests"""
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r["success"])
        failed_tests = total_tests - successful_tests
        
        avg_response_time = sum(r.get("response_time", 0) for r in self.results if r.get("response_time")) / max(successful_tests, 1)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": failed_tests,
            "success_rate": (successful_tests / total_tests * 100) if total_tests > 0 else 0,
            "average_response_time": avg_response_time,
            "results": self.results
        }

    def print_summary(self, report: Dict[str, Any]):
        """Imprime un resumen de los resultados"""
        print("\n" + "="*60)
        print("📊 RESUMEN DE TESTS DE API")
        print("="*60)
        print(f"🕐 Timestamp: {report['timestamp']}")
        print(f"📈 Total de tests: {report['total_tests']}")
        print(f"✅ Tests exitosos: {report['successful_tests']}")
        print(f"❌ Tests fallidos: {report['failed_tests']}")
        print(f"📊 Tasa de éxito: {report['success_rate']:.1f}%")
        print(f"⚡ Tiempo promedio de respuesta: {report['average_response_time']:.3f}s")
        
        if report['failed_tests'] > 0:
            print("\n❌ TESTS FALLIDOS:")
            for result in self.results:
                if not result["success"]:
                    print(f"   • {result['name']}: {result.get('error', f'Status {result.get("status_code", "N/A")}')}")
        
        print("="*60)
        
        if report['success_rate'] >= 95:
            print("🎉 ¡API lista para producción!")
            return True
        elif report['success_rate'] >= 80:
            print("⚠️ API funcional pero con algunos problemas menores")
            return False
        else:
            print("🚨 API no está lista para producción")
            return False

def main():
    parser = argparse.ArgumentParser(
        description="API Health Check Tool para YE&CY COSMETIC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python test_api_health.py
  python test_api_health.py --user=usuario --pass=contraseña
  python test_api_health.py --admin --verbose
  python test_api_health.py --base-url=https://api.ejemplo.com
        """
    )
    
    parser.add_argument('--user', type=str, help='Usuario para autenticación')
    parser.add_argument('--pass', dest='password', type=str, help='Contraseña para autenticación')
    parser.add_argument('--admin', action='store_true', help='Incluir tests de administración')
    parser.add_argument('--verbose', '-v', action='store_true', help='Mostrar información detallada')
    parser.add_argument('--base-url', type=str, default=os.getenv('API_BASE_URL', DEFAULT_BASE_URL),
                       help='URL base de la API')
    parser.add_argument('--timeout', type=int, default=DEFAULT_TIMEOUT,
                       help='Timeout para requests (segundos)')
    
    args = parser.parse_args()
    
    print("""
=== Django API Health Check Tool ===
YE&CY COSMETIC - Testing Completo de API
""")
    
    # Configurar tester
    tester = APITester(args.base_url, args.timeout, args.verbose)
    
    # Obtener credenciales
    username = args.user or os.getenv('API_USER')
    password = args.password or os.getenv('API_PASS')
    admin_username = os.getenv('API_ADMIN_USER')
    admin_password = os.getenv('API_ADMIN_PASS')
    
    if not username and not password:
        print("\n🔑 Para tests completos, proporciona credenciales:")
        print("   Variables de entorno: API_USER, API_PASS")
        print("   Argumentos: --user=usuario --pass=contraseña")
        print("   O ingresa interactivamente:")
        
        try:
            username = input("Usuario: ").strip()
            password = input("Contraseña: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n⚠️ Continuando con tests básicos sin autenticación...")
            username = password = None
    
    # Ejecutar tests
    all_success = True
    
    # 1. Tests públicos
    if not tester.test_public_endpoints():
        all_success = False
    
    # 2. Tests de autenticación
    if username and password:
        if not tester.test_authentication(username, password):
            all_success = False
        
        # Obtener token para tests protegidos
        tester.token = tester.get_jwt_token(username, password)
        if tester.token:
            if not tester.test_protected_endpoints(tester.token):
                all_success = False
        else:
            all_success = False
            print("❌ No se pudo obtener token para tests protegidos")
    
    # 3. Tests de administración
    if args.admin and admin_username and admin_password:
        tester.admin_token = tester.get_jwt_token(admin_username, admin_password)
        if tester.admin_token:
            if not tester.test_admin_endpoints(tester.admin_token):
                all_success = False
        else:
            all_success = False
            print("❌ No se pudo obtener token de admin")
    
    # 4. Tests de manejo de errores
    if not tester.test_error_handling():
        all_success = False
    
    # 5. Tests de rendimiento
    if not tester.test_performance():
        all_success = False
    
    # Generar y mostrar reporte
    report = tester.generate_report()
    production_ready = tester.print_summary(report)
    
    # Guardar reporte en archivo
    report_filename = f"api_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"📄 Reporte guardado en: {report_filename}")
    except Exception as e:
        print(f"⚠️ No se pudo guardar el reporte: {e}")
    
    # Exit code
    if production_ready:
        print("✅ API está lista para producción")
        sys.exit(0)
    else:
        print("❌ API necesita mejoras antes de producción")
        sys.exit(1)

if __name__ == "__main__":
    main()
