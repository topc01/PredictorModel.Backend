from fastapi import APIRouter, HTTPException, status, Body, File, UploadFile, Depends

from app.utils.version import version_manager, ComplexityMapper
from app.core.auth import require_role, get_current_user
from app.models.user import UserRole

router = APIRouter(
    tags=["Models"],
    responses={
        404: {"description": "No encontrado"},
        422: {"description": "Error de validación"},
    },
)

@router.get(
    "/complexities",
    status_code=status.HTTP_200_OK,
    summary="Get all available complexities",
    description="""
    Obtiene la lista completa de complejidades disponibles con sus labels API y nombres reales.
    
    **Uso:** Utiliza los **labels API** (en minúsculas, sin tildes) en tus requests a otros endpoints.
    
    **Ejemplo de respuesta:**
    ```json
    {
      "complexities": [
        {
          "label": "baja",
          "real_name": "Baja",
          "description": "Use 'baja' in API requests"
        },
        {
          "label": "neonatologia",
          "real_name": "Neonatología",
          "description": "Use 'neonatologia' in API requests"
        }
      ]
    }
    ```
    
    **Fuente:** Todos los valores provienen de `ComplexityMapper` en `app/utils/complexities.py`.
    """,
    responses={
        200: {
            "description": "List of all available complexities",
            "content": {
                "application/json": {
                    "example": {
                        "complexities": [
                            {
                                "label": "baja",
                                "real_name": "Baja",
                                "description": "Use 'baja' in API requests"
                            },
                            {
                                "label": "neonatologia",
                                "real_name": "Neonatología",
                                "description": "Use 'neonatologia' in API requests"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def get_complexities(
    current_user: dict = Depends(require_role(UserRole.VIEWER))
):
    """Get all available complexity levels."""
    labels = ComplexityMapper.get_all_labels()
    return {
        "complexities": [
            {
                "label": label.lower(),
                "real_name": ComplexityMapper.to_real_name(label),
                "description": f"Use '{label.lower()}' in API requests"
            }
            for label in labels
        ]
    }

@router.get(
    "/versions",
    status_code=status.HTTP_200_OK,
    summary="Get all models versions",
    description="""
    Obtiene todas las versiones de modelos para **todas las complejidades**.
    
    **Complejidades incluidas:** Todas las definidas en `ComplexityMapper`:
    - Baja, Media, Alta, Neonatología, Pediatría, Inte. Pediátrico, Maternidad
    
    **No requiere parámetros.**
    """,
    responses={
        200: {
            "description": "List of all models versions",
            "content": {
                "application/json": {
                    "example": {
                        "versions": [
                            {
                                "model_name": "prophet_v1_2024-01-01_12-00",
                                "metrics": {
                                    "MAE": 123.45,
                                    "RMSE": 234.56,
                                    "R2": 0.89
                                },
                                "parameters": {
                                    "param1": "value1",
                                    "param2": "value2"
                                }
                            }
                        ]
                    }
                }
            }
        },
        500: {
            "description": "Error retrieving models",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "message": "Failed to retrieve models."
                    }    
                }
            }
        }
    },
)
async def get_all_models(
    current_user: dict = Depends(require_role(UserRole.VIEWER))
):
    return version_manager.get_versions()

@router.get(
    "/versions/{complexity}",
    status_code=status.HTTP_200_OK,
    summary="Get models versions by complexity",
    description="""
    Obtiene las versiones de modelos para una complejidad específica.
    
    **Parámetro `complexity`:** Label API de la complejidad (case-insensitive)
    
    **Valores válidos:** `baja`, `media`, `alta`, `neonatologia`, `pediatria`, `intepediatrico`, `maternidad`
    
    **Ejemplos:**
    - `GET /models/versions/alta`
    - `GET /models/versions/neonatologia`
    
    **Validación:** Usa `ComplexityMapper.is_valid_label()` automáticamente.
    """,
    responses={
        200: {
            "description": "List of models versions by complexity",
            "content": {
                "application/json": {
                    "example": {
                        "versions": [
                            {
                                "model_name": "prophet_v1_2024-01-01_12-00",
                                "metrics": {
                                    "MAE": 123.45,
                                    "RMSE": 234.56,
                                    "R2": 0.89
                                },
                                "parameters": {
                                    "param1": "value1",
                                    "param2": "value2"
                                }
                            }
                        ]
                    }
                }
            }
        },
        500: {
            "description": "Error retrieving models",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "message": "Failed to retrieve models."
                    }    
                }
            }
        }
    },
)
async def get_models_by_complexity(
    complexity: str,
    current_user: dict = Depends(require_role(UserRole.VIEWER))
):
    """Get models versions by complexity."""
    complexity = complexity.lower()
    ComplexityMapper.is_valid_label(complexity)
    return version_manager.get_complexity_versions(complexity)

@router.get(
    "/active",
    status_code=status.HTTP_200_OK,
    summary="Get all active model versions",
    description="""
    Obtiene la configuración completa de versiones activas para **todas las complejidades**.
    
    **Complejidades incluidas:** Todas las definidas en `ComplexityMapper`:
    - Baja, Media, Alta, Neonatología, Pediatría, Inte. Pediátrico, Maternidad
    
    **Retorna:** Un diccionario con los nombres reales (con tildes) como keys.
    
    **No requiere parámetros.**
    """,
    responses={
        200: {
            "description": "Active model configuration",
            "content": {
                "application/json": {
                    "example": {
                        "Alta": {
                            "version": "v1_2024-11-28_01-00-00",
                            "activated_at": "2024-11-28T01:00:00Z",
                            "activated_by": "admin@example.com"
                        },
                        "Baja": {
                            "version": "v1_2024-11-27_10-00-00",
                            "activated_at": "2024-11-27T10:00:00Z",
                            "activated_by": "user@example.com"
                        }
                    }
                }
            }
        }
    }
)
async def get_active_models(
    current_user: dict = Depends(require_role(UserRole.VIEWER))
):
    """Get all active model versions."""
    return version_manager.get_active_versions()

@router.get(
    "/{complexity}/active",
    status_code=status.HTTP_200_OK,
    summary="Get active version for a specific complexity",
    description="""
    Obtiene la versión activa para una complejidad específica.
    
    **Comportamiento:** Si no hay versión activa configurada, retorna automáticamente la versión más reciente.
    
    **Parámetro `complexity`:** Label API de la complejidad (case-insensitive)
    
    **Valores válidos:** `baja`, `media`, `alta`, `neonatologia`, `pediatria`, `intepediatrico`, `maternidad`
    
    **Ejemplos:**
    - `GET /models/alta/active`
    - `GET /models/neonatologia/active`
    
    **Validación:** Usa `ComplexityMapper.is_valid_label()` automáticamente.
    """,
)
async def get_active_model_by_complexity(
    complexity: str,
    current_user: dict = Depends(require_role(UserRole.VIEWER))
):
    complexity = complexity.lower()
    """Get active version for a specific complexity (or latest if none set)."""
    # Validate complexity
    ComplexityMapper.is_valid_label(complexity)

    try:
        # Get the version to use (active or latest)
        version = version_manager.get_active_version(complexity)
        
        # Get metadata for this version
        metadata = version_manager.get_version_metrics(complexity, version)
        
        # Get active version data to check if it's explicitly set
        active_data = version_manager.get_active_version_data(complexity)
        is_explicitly_set = bool(active_data.get("version"))
        
        return {
            "complexity": complexity,
            "version": version,
            "activated_at": active_data.get("activated_at") if is_explicitly_set else None,
            "activated_by": active_data.get("activated_by") if is_explicitly_set else None,
            "is_explicitly_set": is_explicitly_set,
            "metadata": metadata
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving active model: {str(e)}"
        )

@router.get(
    "/{complexity}/versions/{version_id}",
    status_code=status.HTTP_200_OK,
    summary="Get metadata for a specific version",
    description="""
    Obtiene los metadatos detallados de una versión específica de modelo.
    
    **Parámetros:**
    - `complexity`: Label API de la complejidad (case-insensitive)
    - `version_id`: Identificador de la versión (ej: `v1_2024-11-28_01-00-00`)
    
    **Valores válidos para complexity:** `baja`, `media`, `alta`, `neonatologia`, `pediatria`, `intepediatrico`, `maternidad`
    
    **Ejemplo:**
    - `GET /models/alta/versions/v1_2024-11-28_01-00-00`
    
    **Validación:** Usa `ComplexityMapper.is_valid_label()` automáticamente.
    """,
)
async def get_version_details(
    complexity: str,
    version: str,
    current_user: dict = Depends(require_role(UserRole.VIEWER))
):
    complexity = complexity.lower()
    """Get metadata for a specific version."""
    # Validate complexity
    ComplexityMapper.is_valid_label(complexity)

    metadata = version_manager.get_version_metrics(complexity, version)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version} not found for complexity: {complexity}"
        )
    return metadata


@router.put(
    "/{complexity}/active",
    status_code=status.HTTP_200_OK,
    summary="Activate model version",
    description="""
    Activa una versión específica de modelo para una complejidad.
    
    **Parámetro `complexity`:** Label API de la complejidad (case-insensitive)
    
    **Valores válidos:** `baja`, `media`, `alta`, `neonatologia`, `pediatria`, `intepediatrico`, `maternidad`
    
    **Body:**
    ```json
    {
      "version": "v1_2024-11-28_01-00-00",
      "user": "admin@example.com"
    }
    ```
    
    **Ejemplo:**
    - `PUT /models/alta/active`
    
    **Validación:** Usa `ComplexityMapper.is_valid_label()` automáticamente.
    """,
    responses={
        200: {
            "description": "Model version activated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Model version activated successfully",
                        "data": {
                            "version": "v1_2024-11-28_01-00-00",
                            "activated_at": "2024-11-28T01:00:00Z",
                            "activated_by": "system"
                        }
                    }
                }
            }
        },
        404: {
            "description": "Version not found"
        }
    },
)
async def activate_model_version(
    complexity: str,
    request: dict = Body(..., example={"version": "v1_2024-11-28_01-00-00", "user": "admin@example.com"}),
    current_user: dict = Depends(require_role(UserRole.ADMIN))
):
    """Activate a specific model version."""
    # Validate complexity
    complexity = complexity.lower()
    ComplexityMapper.is_valid_label(complexity)

    version = request.get("version")
    user = request.get("user", "system")
    
    if not version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Version is required"
        )
    
    # Verify version exists
    metadata = version_manager.get_version_metrics(complexity, version)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version} not found for complexity: {complexity}"
        )
    
    result = version_manager.set_active_version(complexity, version, user)
    return {
        "status": "success",
        "message": f"Model version {version} activated for {complexity}",
        "data": result
    }

@router.put(
    "/active/batch",
    status_code=status.HTTP_200_OK,
    summary="Activate multiple model versions",
    description="""
    Activa múltiples versiones de modelos a la vez.
    
    **IMPORTANTE:** Este endpoint usa **nombres reales** (con tildes) en el body, no labels API.
    
    **Body:**
    ```json
    {
      "versions": {
        "Alta": "v1_2024-11-28_01-00-00",
        "Baja": "v2_2024-11-27_10-00-00",
        "Neonatología": "v1_2024-11-27_15-00-00"
      },
      "user": "admin@example.com"
    }
    ```
    
    **Nota:** Usa `ComplexityMapper.get_all_real_names()` para obtener los nombres correctos.
    """,
)
async def activate_models_batch(
    request: dict = Body(..., example={
        "versions": {
            "Alta": "v1_2024-11-28_01-00-00",
            "Baja": "v2_2024-11-27_10-00-00"
        },
        "user": "admin@example.com"
    }),
    current_user: dict = Depends(require_role(UserRole.ADMIN))
):
    """Activate multiple model versions at once."""
    versions_dict = request.get("versions", {})
    user = request.get("user", "system")
    
    if not versions_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Versions dictionary is required"
        )
    
    # Verify all versions exist
    for complexity, version in versions_dict.items():
        metadata = version_manager.get_version_metrics(complexity, version)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {version} not found for complexity: {complexity}"
            )
    
    result = version_manager.set_active_versions_batch(versions_dict, user)
    return {
        "status": "success",
        "message": f"Activated {len(versions_dict)} model versions",
        "data": result
    }
