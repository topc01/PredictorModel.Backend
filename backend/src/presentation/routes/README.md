# Estructura de Rutas Modularizada

Esta carpeta contiene todas las rutas de la API organizadas por módulos funcionales.

## Estructura Actual

```
routes/
├── __init__.py          # Router principal que combina todas las rutas
├── auth.py              # Rutas de autenticación
├── example.py           # Ejemplo de cómo agregar nuevas rutas
└── README.md            # Esta documentación
```

## Cómo Agregar Nuevas Rutas

### 1. Crear un nuevo archivo de rutas

Crea un archivo en esta carpeta, por ejemplo `users.py`:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/users", tags=["Users"])

@router.get("/")
def get_users():
    return {"users": []}

@router.post("/")
def create_user():
    return {"message": "User created"}
```

### 2. Registrar el router en `__init__.py`

```python
from fastapi import APIRouter
from .auth import router as auth_router
from .users import router as users_router  # Nueva importación

main_router = APIRouter()

# Incluir todas las rutas
main_router.include_router(auth_router)
main_router.include_router(users_router)  # Nueva línea
```

### 3. Las rutas estarán disponibles automáticamente

Una vez registradas, las rutas estarán disponibles en:
- `http://localhost:8000/api/v1/users/`
- `http://localhost:8000/api/v1/auth/`

## Convenciones

- **Prefijo de rutas**: Usar `/api/v1/` para todas las rutas
- **Tags**: Usar tags descriptivos para la documentación Swagger
- **Nombres de archivos**: Usar nombres descriptivos en minúsculas
- **Imports**: Usar imports relativos dentro del módulo

## Ejemplos de Módulos Comunes

- `auth.py` - Autenticación y autorización
- `users.py` - Gestión de usuarios
- `products.py` - Catálogo de productos
- `orders.py` - Gestión de pedidos
- `admin.py` - Funciones administrativas
- `health.py` - Health checks y monitoreo
