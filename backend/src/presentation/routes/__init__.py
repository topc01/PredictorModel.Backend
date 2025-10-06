from fastapi import APIRouter
from .auth import router as auth_router

# Crear el router principal que combina todas las rutas
main_router = APIRouter()

# Incluir todas las rutas de módulos
main_router.include_router(auth_router)

__all__ = ["main_router"]
