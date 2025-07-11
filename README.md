# YE&CY COSMETIC - Tienda Online de Cosméticos

## Estructura del Proyecto

```
backend/
├── .env
├── .gitignore
├── README.md
├── db.sqlite3
├── inventario/
├── logs/
├── manage.py
├── render.yaml
├── requirements.txt
├── static/
├── staticfiles/
├── tienda/
├── yecy_cosmetic/
```

El backend Django está completamente autocontenido en la carpeta `backend`. El frontend profesional (HTML+JS+Tailwind CSS) se encuentra en la carpeta `../frontend`.

---

## Descripción
YE&CY COSMETIC es una tienda online de cosméticos moderna y profesional desarrollada con Django y Tailwind CSS. La plataforma permite a los clientes explorar productos de belleza, realizar compras y gestionar sus pedidos.

## Características Principales

### Frontend
- Diseño moderno y responsive con Tailwind CSS
- Sistema de categorías y subcategorías
- Búsqueda de productos en tiempo real
- Sistema de carrito de compras
- Integración con WhatsApp para compras
- Sistema de calificaciones y comentarios
- Perfil de usuario con historial de compras
- Gráficos de estadísticas de compras
- Atención al cliente vía WhatsApp

### Backend
- Gestión de inventario con categorías y subcategorías
- Sistema de pedidos con estados (pendiente, completado, cancelado)
- Sistema de autenticación para clientes y administradores
- Panel de administración para gestión de productos y ventas
- Generación de PDFs para pedidos
- Sistema de permisos y roles

## Requisitos Técnicos

### Backend
- Python 3.11+
- Django 5.x
- PostgreSQL (Neon.tech)
- Django REST framework
- Django CORS headers
- Django Channels para funcionalidades en tiempo real

### Frontend
- HTML5
- JavaScript (ES6+)
- Tailwind CSS
- Chart.js para gráficos
- PDF.js para generación de PDFs
- Axios para peticiones HTTP

## Configuración

### Variables de Entorno
```bash
# Base de datos
DATABASE_URL=postgresql://neondb_owner:npg_Bmu73FJRqDxH@ep-quiet-queen-a8qi5i2c-pooler.eastus2.azure.neon.tech/neondb?sslmode=require&channel_binding=require

# Configuración de producción
DEBUG=False
SECRET_KEY=tu_clave_secreta
ALLOWED_HOSTS=*.render.com,localhost

# Configuración de seguridad
CSRF_TRUSTED_ORIGINS=https://*.render.com
```

## Estructura del Proyecto
```
yecy_cosmetic/
├── backend/              # Aplicación Django
│   ├── yecy_cosmetic/   # Configuración del proyecto
│   ├── tienda/          # Aplicación de la tienda
│   └── inventario/      # Aplicación del inventario
├── frontend/            # Frontend estático
│   ├── static/          # Archivos estáticos
│   └── templates/       
│       ├── cliente/     # Templates del cliente
│       └── admin/       # Templates del administrador
└── .env                 # Variables de entorno
```

## Despliegue
El proyecto está configurado para desplegarse en Render.com con soporte tanto para desarrollo como producción.

## Licencia
MIT
