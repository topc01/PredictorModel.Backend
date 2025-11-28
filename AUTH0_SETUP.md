# Configuración de Auth0

Esta guía te ayudará a configurar Auth0 para el sistema de autenticación del backend.

## 📋 Requisitos Previos

- Cuenta de Auth0 (puedes crear una gratuita en [auth0.com](https://auth0.com))
- Acceso al Dashboard de Auth0

---

## 🔧 Paso 1: Crear una API en Auth0

1. Ve al [Dashboard de Auth0](https://manage.auth0.com/)
2. Navega a **Applications** → **APIs**
3. Haz clic en **Create API**
4. Completa el formulario:
   - **Name**: `Predictor Model API` (o el nombre que prefieras)
   - **Identifier**: `https://predictor-model-api` (debe ser una URL única, guárdala para las variables de entorno)
   - **Signing Algorithm**: `RS256` (recomendado)
5. Haz clic en **Create**

### Habilitar RBAC (Role-Based Access Control)

1. En la página de tu API, ve a la pestaña **Settings**
2. Desplázate hasta **RBAC Settings**
3. Activa las siguientes opciones:
   - ✅ **Enable RBAC**
   - ✅ **Add Permissions in the Access Token**
4. Haz clic en **Save**

---

## 👥 Paso 2: Crear Roles

1. En el Dashboard, ve a **User Management** → **Roles**
2. Haz clic en **Create Role**

### Crear Rol "administrador"

1. **Name**: `administrador`
2. **Description**: `Rol con acceso completo, puede gestionar usuarios`
3. Haz clic en **Create**
4. (Opcional) En la pestaña **Permissions**, puedes agregar permisos específicos si lo deseas

### Crear Rol "visualizador"

1. **Name**: `visualizador`
2. **Description**: `Rol de solo lectura, puede ver datos pero no modificarlos`
3. Haz clic en **Create**

---

## 🔐 Paso 3: Crear Aplicación Machine-to-Machine (M2M)

Esta aplicación se usa para que el backend se comunique con Auth0 Management API.

1. Ve a **Applications** → **Applications**
2. Haz clic en **Create Application**
3. Completa el formulario:
   - **Name**: `Predictor Model Backend M2M`
   - **Application Type**: Selecciona **Machine to Machine Applications**
4. Haz clic en **Create**
5. En la siguiente pantalla, selecciona la API que creaste en el Paso 1
6. Autoriza la aplicación y expande la sección **Authorized Scopes**
7. Selecciona los siguientes scopes (permisos):
   - `read:users` - Para listar y obtener usuarios
   - `create:users` - Para crear usuarios
   - `update:users` - Para actualizar usuarios
   - `delete:users` - Para eliminar usuarios
   - `read:roles` - Para listar roles
   - `create:user_tickets` - Para enviar invitaciones
   - `update:roles` - Para asignar roles a usuarios
8. Haz clic en **Authorize**
9. Ve a la pestaña **Settings** de la aplicación M2M
10. Copia los siguientes valores (los necesitarás para las variables de entorno):
    - **Domain**: El dominio de tu tenant (ej: `your-tenant.auth0.com`)
    - **Client ID**: El ID de la aplicación M2M
    - **Client Secret**: El secreto de la aplicación M2M (muéstralo y cópialo)

---

## 🚫 Paso 4: Deshabilitar Registro Público

Para que solo los administradores puedan crear usuarios:

1. Ve a **Authentication** → **Database**
2. Selecciona tu conexión (por defecto: `Username-Password-Authentication`)
3. En la pestaña **Settings**, desplázate hasta **Disable Sign Ups**
4. Activa **Disable Sign Ups**
5. Haz clic en **Save**

---

## 🔗 Paso 5: Configurar URLs de Callback (Opcional)

Si tienes un frontend que se conecta a Auth0:

1. Ve a **Applications** → **Applications**
2. Selecciona tu aplicación frontend (o crea una nueva de tipo **Single Page Application**)
3. En **Allowed Callback URLs**, agrega:
   - `http://localhost:5173` (para desarrollo local)
   - `https://main.d12abg5dtejald.amplifyapp.com` (para producción)
   - `https://develop.d12abg5dtejald.amplifyapp.com` (para desarrollo)
4. En **Allowed Logout URLs**, agrega las mismas URLs
5. Haz clic en **Save Changes**

---

## ⚙️ Paso 6: Configurar Variables de Entorno

Crea o actualiza tu archivo `.env` en el directorio `backend/` con las siguientes variables:

```env
# Auth0 Configuration
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_API_AUDIENCE=https://predictor-model-api
AUTH0_ISSUER=https://your-tenant.auth0.com/
AUTH0_ALGORITHMS=RS256

# Auth0 Management API (for user management)
AUTH0_MANAGEMENT_API_DOMAIN=your-tenant.auth0.com
AUTH0_MANAGEMENT_API_CLIENT_ID=your-m2m-client-id
AUTH0_MANAGEMENT_API_CLIENT_SECRET=your-m2m-client-secret
```

**Nota**: Reemplaza los valores con los de tu configuración de Auth0:
- `AUTH0_DOMAIN`: El dominio de tu tenant (ej: `mi-empresa.auth0.com`)
- `AUTH0_API_AUDIENCE`: El Identifier de la API que creaste en el Paso 1
- `AUTH0_ISSUER`: Generalmente es `https://your-tenant.auth0.com/`
- `AUTH0_MANAGEMENT_API_CLIENT_ID` y `AUTH0_MANAGEMENT_API_CLIENT_SECRET`: Los valores de la aplicación M2M del Paso 3

---

## 👤 Paso 7: Crear el Primer Usuario Administrador

Como deshabilitaste el registro público, necesitas crear el primer usuario administrador desde el Dashboard de Auth0:

1. Ve a **User Management** → **Users**
2. Haz clic en **Create User**
3. Completa el formulario:
   - **Email**: El email del administrador
   - **Password**: Una contraseña segura
   - **Connection**: `Username-Password-Authentication`
4. Haz clic en **Create**
5. Una vez creado, haz clic en el usuario
6. Ve a la pestaña **Roles**
7. Haz clic en **Assign Roles**
8. Selecciona el rol `administrador`
9. Haz clic en **Assign**

---

## ✅ Paso 8: Verificar la Configuración

1. Asegúrate de que todas las variables de entorno estén configuradas correctamente
2. Reinicia el servidor backend
3. Intenta autenticarte con el usuario administrador que creaste
4. Verifica que puedas acceder a los endpoints protegidos
5. Prueba crear un nuevo usuario usando el endpoint `/users/invite` (solo administradores)

---

## 🔍 Troubleshooting

### Error: "AUTH0_DOMAIN environment variable is required"

**Solución**: Verifica que todas las variables de entorno de Auth0 estén configuradas en tu archivo `.env`.

### Error: "Failed to get Management API token"

**Solución**: 
- Verifica que `AUTH0_MANAGEMENT_API_CLIENT_ID` y `AUTH0_MANAGEMENT_API_CLIENT_SECRET` sean correctos
- Asegúrate de que la aplicación M2M tenga los permisos necesarios en la API

### Error: "Invalid token" o "Token has expired"

**Solución**: 
- Verifica que el token JWT sea válido y no haya expirado
- Asegúrate de que `AUTH0_API_AUDIENCE` coincida con el Identifier de tu API en Auth0
- Verifica que `AUTH0_ISSUER` sea correcto

### Error: "Insufficient permissions" o "Administrator role required"

**Solución**: 
- Verifica que el usuario tenga el rol `administrador` asignado en Auth0
- Asegúrate de que RBAC esté habilitado en tu API
- Verifica que los roles estén incluidos en el token de acceso

### Los roles no aparecen en el token

**Solución**:
1. Ve a tu API en Auth0 Dashboard
2. Asegúrate de que **Add Permissions in the Access Token** esté activado en RBAC Settings
3. Verifica que el usuario tenga roles asignados
4. Cuando solicites el token, asegúrate de incluir el scope `read:roles` si es necesario

---

## 📚 Recursos Adicionales

- [Documentación de Auth0](https://auth0.com/docs)
- [Auth0 Management API](https://auth0.com/docs/api/management/v2)
- [RBAC en Auth0](https://auth0.com/docs/authorization/rbac)
- [JWT Tokens](https://auth0.com/docs/secure/tokens/json-web-tokens)

---

## 🔒 Seguridad

- **Nunca** commits el archivo `.env` al repositorio
- Mantén seguros los `AUTH0_MANAGEMENT_API_CLIENT_SECRET`
- Usa diferentes aplicaciones M2M para desarrollo y producción
- Revisa regularmente los permisos de las aplicaciones M2M
- Considera usar rotación de secretos para aplicaciones M2M en producción

