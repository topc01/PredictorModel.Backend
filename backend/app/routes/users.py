"""
User management routes (admin only).

These endpoints allow administrators to manage users via Auth0 Management API.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Body
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict
from app.auth import require_admin
from app.auth.management_api import management_api


router = APIRouter(
    prefix="/users",
    tags=["Users"],
    responses={
        401: {"description": "No autorizado"},
        403: {"description": "Permisos insuficientes"},
        404: {"description": "Usuario no encontrado"},
    },
)


class InviteUserRequest(BaseModel):
    """Request model for inviting a user."""
    email: EmailStr = Field(..., description="Email del usuario a invitar")
    connection: str = Field(
        default="Username-Password-Authentication",
        description="Conexión de Auth0 a usar"
    )
    role: str = Field(
        default="visualizador",
        description="Rol a asignar al usuario (visualizador o administrador)"
    )


class InviteUserResponse(BaseModel):
    """Response model for user invitation."""
    message: str = Field(..., description="Mensaje de confirmación")
    email: str = Field(..., description="Email del usuario invitado")
    invitation_url: Optional[str] = Field(None, description="URL de invitación")


class UpdateUserRoleRequest(BaseModel):
    """Request model for updating user role."""
    role: str = Field(..., description="Nuevo rol (visualizador o administrador)")


@router.post(
    "/invite",
    status_code=status.HTTP_201_CREATED,
    summary="Invitar usuario",
    description="""
    Envía una invitación por email a un nuevo usuario.
    
    Solo los administradores pueden invitar usuarios.
    El usuario recibirá un email con un link para completar su registro.
    
    **Roles disponibles:**
    - `visualizador`: Solo lectura
    - `administrador`: Acceso completo
    """,
    response_model=InviteUserResponse,
    responses={
        201: {
            "description": "Invitación enviada correctamente",
        },
        400: {
            "description": "Error en la solicitud",
        },
    },
)
async def invite_user(
    request: InviteUserRequest,
    admin_user: dict = Depends(require_admin),
):
    """
    Invita a un nuevo usuario al sistema.
    
    El usuario recibirá un email con instrucciones para completar su registro.
    """
    # Validate role
    valid_roles = ["visualizador", "administrador"]
    if request.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rol inválido. Roles permitidos: {', '.join(valid_roles)}"
        )
    
    try:
        # First, get all roles to find the role ID
        roles = await management_api.list_roles()
        role_id = None
        
        for role in roles:
            if role.get("name") == request.role:
                role_id = role.get("id")
                break
        
        if not role_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Rol '{request.role}' no encontrado en Auth0"
            )
        
        # Create user invitation
        invite_result = await management_api.invite_user(
            email=request.email,
            connection=request.connection,
        )
        
        user_id = invite_result.get("user_id")
        if user_id:
            # Assign role to the user
            await management_api.assign_roles(user_id, [role_id])
        
        return InviteUserResponse(
            message="Invitación enviada correctamente",
            email=request.email,
            invitation_url=invite_result.get("ticket"),
        )
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al invitar usuario: {str(e)}"
        )


@router.get(
    "",
    summary="Listar usuarios",
    description="""
    Obtiene una lista de todos los usuarios del sistema.
    
    Solo los administradores pueden ver la lista de usuarios.
    """,
    responses={
        200: {
            "description": "Lista de usuarios",
            "content": {
                "application/json": {
                    "example": {
                        "users": [
                            {
                                "user_id": "auth0|123456",
                                "email": "user@example.com",
                                "email_verified": True,
                                "roles": ["visualizador"]
                            }
                        ],
                        "total": 1
                    }
                }
            }
        },
    },
)
async def list_users(
    page: int = 0,
    per_page: int = 50,
    admin_user: dict = Depends(require_admin),
):
    """
    Lista todos los usuarios del sistema.
    """
    try:
        result = await management_api.list_users(page=page, per_page=per_page)
        users = result.get("users", [])
        total = result.get("total", len(users))
        
        # Enrich users with their roles
        enriched_users = []
        for user in users:
            user_id = user.get("user_id")
            if user_id:
                try:
                    roles = await management_api.get_user_roles(user_id)
                    user["roles"] = [role.get("name") for role in roles]
                except:
                    user["roles"] = []
            else:
                user["roles"] = []
            
            enriched_users.append({
                "user_id": user.get("user_id"),
                "email": user.get("email"),
                "email_verified": user.get("email_verified", False),
                "created_at": user.get("created_at"),
                "updated_at": user.get("updated_at"),
                "roles": user["roles"],
            })
        
        return {
            "users": enriched_users,
            "total": total,
            "page": page,
            "per_page": per_page,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar usuarios: {str(e)}"
        )


@router.get(
    "/{user_id}",
    summary="Obtener usuario",
    description="""
    Obtiene información detallada de un usuario específico.
    
    Solo los administradores pueden ver información de usuarios.
    """,
    responses={
        200: {
            "description": "Información del usuario",
        },
        404: {
            "description": "Usuario no encontrado",
        },
    },
)
async def get_user(
    user_id: str,
    admin_user: dict = Depends(require_admin),
):
    """
    Obtiene información detallada de un usuario.
    """
    try:
        user = await management_api.get_user(user_id)
        roles = await management_api.get_user_roles(user_id)
        
        return {
            "user_id": user.get("user_id"),
            "email": user.get("email"),
            "email_verified": user.get("email_verified", False),
            "created_at": user.get("created_at"),
            "updated_at": user.get("updated_at"),
            "roles": [role.get("name") for role in roles],
            "user_metadata": user.get("user_metadata", {}),
        }
        
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario {user_id} no encontrado"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener usuario: {error_msg}"
        )


@router.patch(
    "/{user_id}/role",
    summary="Cambiar rol de usuario",
    description="""
    Cambia el rol de un usuario.
    
    Solo los administradores pueden cambiar roles de usuarios.
    
    **Roles disponibles:**
    - `visualizador`: Solo lectura
    - `administrador`: Acceso completo
    """,
    responses={
        200: {
            "description": "Rol actualizado correctamente",
        },
        400: {
            "description": "Rol inválido",
        },
        404: {
            "description": "Usuario no encontrado",
        },
    },
)
async def update_user_role(
    user_id: str,
    request: UpdateUserRoleRequest,
    admin_user: dict = Depends(require_admin),
):
    """
    Cambia el rol de un usuario.
    """
    # Validate role
    valid_roles = ["visualizador", "administrador"]
    if request.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rol inválido. Roles permitidos: {', '.join(valid_roles)}"
        )
    
    try:
        # Get all roles to find the role ID
        roles = await management_api.list_roles()
        role_id = None
        
        for role in roles:
            if role.get("name") == request.role:
                role_id = role.get("id")
                break
        
        if not role_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Rol '{request.role}' no encontrado en Auth0"
            )
        
        # Get current user roles
        current_roles = await management_api.get_user_roles(user_id)
        current_role_ids = [role.get("id") for role in current_roles]
        
        # Remove all current roles
        if current_role_ids:
            await management_api.remove_roles(user_id, current_role_ids)
        
        # Assign new role
        await management_api.assign_roles(user_id, [role_id])
        
        return {
            "message": "Rol actualizado correctamente",
            "user_id": user_id,
            "new_role": request.role,
        }
        
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario {user_id} no encontrado"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar rol: {error_msg}"
        )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar usuario",
    description="""
    Elimina un usuario del sistema.
    
    Solo los administradores pueden eliminar usuarios.
    Esta acción no se puede deshacer.
    """,
    responses={
        204: {
            "description": "Usuario eliminado correctamente",
        },
        404: {
            "description": "Usuario no encontrado",
        },
    },
)
async def delete_user(
    user_id: str,
    admin_user: dict = Depends(require_admin),
):
    """
    Elimina un usuario del sistema.
    """
    try:
        await management_api.delete_user(user_id)
        return None
        
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario {user_id} no encontrado"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar usuario: {error_msg}"
        )

