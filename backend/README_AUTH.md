# Sistema de Autenticación JWT

Este sistema implementa autenticación JWT siguiendo arquitectura limpia con FastAPI.

## Estructura del Proyecto

```
src/
├── domain/           # Entidades y reglas de negocio
│   ├── entities.py   # User, Token, RefreshToken
│   ├── repositories.py # Interfaces de repositorios
│   └── services.py   # Interfaces de servicios
├── application/      # Casos de uso y DTOs
│   ├── dtos.py       # DTOs de request/response
│   └── use_cases.py  # Casos de uso de autenticación
├── infrastructure/   # Implementaciones concretas
│   ├── config.py     # Configuración de la aplicación
│   ├── database.py   # Modelos de base de datos
│   ├── repositories.py # Implementación de repositorios
│   └── services.py   # Implementación de servicios
└── presentation/     # API y controladores
    ├── middleware.py # Middleware de autenticación
    ├── controllers.py # Controladores de autenticación
    └── routes.py     # Rutas de la API
```

## Endpoints Disponibles

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/auth/login` | Autenticar y generar JWT |
| POST | `/api/v1/auth/logout` | Revocar token |
| POST | `/api/v1/auth/refresh` | Renovar access token |
| GET | `/api/v1/auth/me` | Info del usuario autenticado |

## Configuración

1. Copia `.env.example` a `.env` y configura las variables:

```bash
cp .env.example .env
```

2. Configura la base de datos PostgreSQL:

```env
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/predictor_db
SECRET_KEY=your-super-secret-key-change-in-production
```

3. Instala las dependencias:

```bash
uv sync
```

4. Inicializa la base de datos:

```bash
uv run python src/infrastructure/database_init.py
```

5. Crea un usuario de prueba:

```bash
uv run python src/utils/create_user.py
```

## Uso de la API

### 1. Login

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'
```

Respuesta:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 2. Obtener información del usuario

```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 3. Renovar token

```bash
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "YOUR_REFRESH_TOKEN"
  }'
```

### 4. Logout

```bash
curl -X POST "http://localhost:8000/api/v1/auth/logout" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "YOUR_REFRESH_TOKEN"
  }'
```

## Características

- **JWT con access y refresh tokens**
- **Arquitectura limpia** con separación de capas
- **Validación robusta** de inputs
- **Manejo de errores** estructurado
- **Tipado completo** con type hints
- **Seguridad** con hash de contraseñas bcrypt
- **Middleware de autenticación** automático
- **CORS configurado** para desarrollo

## Desarrollo

Para ejecutar en modo desarrollo:

```bash
uv run dev
```

El servidor estará disponible en `http://localhost:8000`

Para ver la documentación interactiva:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
