# Testing de API - YE&CY COSMETIC

Este directorio contiene herramientas completas para testing de la API de Django antes de pasar a producción.

## 📁 Archivos de Testing

- `test_api_health.py` - Script principal de testing de API
- `test_config.py` - Configuración para diferentes entornos
- `install_test_deps.py` - Instalador de dependencias
- `README_TESTING.md` - Esta documentación

## 🚀 Instalación y Configuración

### 1. Instalar Dependencias

```bash
# Instalar dependencias de testing
python install_test_deps.py

# O manualmente
pip install requests pytest pytest-django pytest-cov factory-boy faker
```

### 2. Configurar Variables de Entorno (Opcional)

```bash
# Para desarrollo
export API_USER="tu_usuario"
export API_PASS="tu_contraseña"
export API_BASE_URL="http://127.0.0.1:8000/"

# Para staging
export API_ENV="staging"
export STAGING_TEST_USER="usuario_test"
export STAGING_TEST_PASS="pass_test"

# Para producción
export API_ENV="production"
export PROD_TEST_USER="usuario_prod"
export PROD_TEST_PASS="pass_prod"
```

## 🧪 Ejecutar Tests

### Testing Básico

```bash
# Test básico sin autenticación
python test_api_health.py

# Test con información detallada
python test_api_health.py --verbose

# Test con credenciales específicas
python test_api_health.py --user=usuario --pass=contraseña
```

### Testing Completo

```bash
# Test completo con autenticación
python test_api_health.py --user=usuario --pass=contraseña --verbose

# Test incluyendo endpoints de administración
python test_api_health.py --user=usuario --pass=contraseña --admin --verbose

# Test en entorno específico
API_ENV=staging python test_api_health.py --verbose
```

### Testing de Producción

```bash
# Test de producción (requiere credenciales reales)
API_ENV=production python test_api_health.py --user=usuario_real --pass=pass_real --verbose
```

## 📊 Qué Testea el Script

### 1. Endpoints Públicos
- ✅ API Root (`/`)
- ✅ Productos Destacados (`/api/cliente/productos/destacados/`)
- ✅ Categorías (`/api/cliente/categorias/`)
- ✅ Verificación de Token (sin token válido)

### 2. Sistema de Autenticación
- ✅ Registro de usuarios
- ✅ Login con número de teléfono
- ✅ Login fallido (validación de errores)
- ✅ Obtención de tokens JWT

### 3. Endpoints Protegidos
- ✅ Perfil de usuario
- ✅ Carrito de compras
- ✅ Añadir productos al carrito
- ✅ Limpiar carrito
- ✅ Historial de compras
- ✅ Estadísticas del cliente
- ✅ Notificaciones
- ✅ Historial de acciones

### 4. Endpoints de Administración
- ✅ Estadísticas globales
- ✅ Gestión de compras
- ✅ CRUD de categorías
- ✅ CRUD de productos
- ✅ Estados de venta

### 5. Manejo de Errores
- ✅ Endpoints inexistentes (404)
- ✅ Métodos no permitidos (405)
- ✅ Acceso no autorizado (401)

### 6. Rendimiento
- ✅ Tiempo de respuesta
- ✅ Timeouts
- ✅ Latencia promedio

## 📈 Criterios de Aceptación para Producción

Para que la API se considere lista para producción, debe cumplir:

- ✅ **Tasa de éxito ≥ 95%** - Al menos 95% de los endpoints funcionan correctamente
- ✅ **Tiempo promedio ≤ 2 segundos** - Respuesta rápida
- ✅ **Endpoints críticos funcionando** - Registro, login, productos, categorías
- ✅ **Autenticación funcionando** - Sistema JWT operativo
- ✅ **Manejo de errores correcto** - Respuestas apropiadas para errores

## 📋 Reportes

El script genera reportes detallados:

### En Consola
```
=== Django API Health Check Tool ===
YE&CY COSMETIC - Testing Completo de API

[14:30:15] [INFO] 🔍 Testing endpoints públicos...
[14:30:15] [SUCCESS] ✅ API Root (GET http://127.0.0.1:8000/) - Status: 200
[14:30:16] [SUCCESS] ✅ Productos Destacados (GET http://127.0.0.1:8000/api/cliente/productos/destacados/) - Status: 200
...

============================================================
📊 RESUMEN DE TESTS DE API
============================================================
🕐 Timestamp: 2024-01-15T14:30:20
📈 Total de tests: 25
✅ Tests exitosos: 24
❌ Tests fallidos: 1
📊 Tasa de éxito: 96.0%
⚡ Tiempo promedio de respuesta: 0.245s
============================================================
🎉 ¡API lista para producción!
```

### Archivo JSON
Se guarda un reporte completo en `api_test_report_YYYYMMDD_HHMMSS.json` con:
- Resultados detallados de cada endpoint
- Tiempos de respuesta
- Errores específicos
- Métricas de rendimiento

## 🔧 Configuración Avanzada

### Entornos Predefinidos

El script soporta diferentes entornos:

```python
# Development (localhost)
API_ENV=development

# Staging (servidor de pruebas)
API_ENV=staging

# Production (servidor real)
API_ENV=production
```

### Configuración Personalizada

Puedes modificar `test_config.py` para:
- Agregar nuevos endpoints
- Cambiar criterios de aceptación
- Configurar timeouts específicos
- Definir usuarios de test

### Variables de Entorno Disponibles

| Variable | Descripción | Default |
|----------|-------------|---------|
| `API_ENV` | Entorno de testing | `development` |
| `API_BASE_URL` | URL base de la API | `http://127.0.0.1:8000/` |
| `API_USER` | Usuario para testing | - |
| `API_PASS` | Contraseña para testing | - |
| `API_ADMIN_USER` | Usuario admin | - |
| `API_ADMIN_PASS` | Contraseña admin | - |

## 🚨 Troubleshooting

### Error: "Unable to import 'requests'"
```bash
pip install requests
```

### Error: "Connection refused"
- Verifica que Django esté corriendo: `python manage.py runserver`
- Verifica la URL base en la configuración

### Error: "Authentication failed"
- Verifica las credenciales
- Asegúrate de que el usuario existe en la base de datos
- Verifica que el endpoint de token funcione

### Tests fallando en producción
- Verifica que los endpoints estén habilitados
- Revisa los logs de Django
- Verifica la configuración de CORS
- Asegúrate de que la base de datos esté accesible

## 📝 Integración con CI/CD

### GitHub Actions
```yaml
name: API Health Check
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          python install_test_deps.py
      - name: Run API tests
        run: |
          python manage.py runserver &
          sleep 10
          python test_api_health.py --verbose
```

### GitLab CI
```yaml
api_test:
  stage: test
  script:
    - pip install -r requirements.txt
    - python install_test_deps.py
    - python manage.py runserver &
    - sleep 10
    - python test_api_health.py --verbose
```

## 🤝 Contribuir

Para mejorar las herramientas de testing:

1. Agrega nuevos endpoints en `test_config.py`
2. Implementa nuevos tipos de tests en `test_api_health.py`
3. Actualiza la documentación
4. Ejecuta los tests existentes para verificar que no rompas nada

## 📞 Soporte

Si encuentras problemas:

1. Revisa los logs de Django
2. Verifica la configuración en `test_config.py`
3. Ejecuta con `--verbose` para más detalles
4. Revisa el reporte JSON generado

---

**Nota**: Este testing es complementario a los tests unitarios de Django. Se recomienda ejecutar ambos antes de cada deploy a producción. 