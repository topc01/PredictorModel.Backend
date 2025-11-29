from fastapi import APIRouter, HTTPException, status, Body, File, UploadFile

from app.utils.version import version_manager

router = APIRouter(
    tags=["Models"],
    responses={
        404: {"description": "No encontrado"},
        422: {"description": "Error de validación"},
    },
)

@router.get(
    "/versions",
    status_code=status.HTTP_200_OK,
    summary="Get all models versions",
    description="""
    Endpoint to retrieve all models versions.
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
async def get_all_models():
    return version_manager.get_versions()

@router.get(
    "/versions/{complexity}",
    status_code=status.HTTP_200_OK,
    summary="Get models versions by complexity",
    description="""
    Endpoint to retrieve models versions by complexity.
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
async def get_models_by_complexity(complexity: str):
    return version_manager.get_complexity_versions(complexity)

@router.get(
    "/active",
    status_code=status.HTTP_200_OK,
    summary="Get all active model versions",
    description="""
    Get the complete configuration of active model versions for all complexities.
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
async def get_active_models():
    """Get all active model versions."""
    return version_manager.get_active_versions()

@router.get(
    "/{complexity}/active",
    status_code=status.HTTP_200_OK,
    summary="Get active version for a specific complexity",
    description="""
    Get the active version information for a specific complexity.
    
    If no active version is configured, automatically returns the latest version.
    """,
)
async def get_active_model_by_complexity(complexity: str):
    """Get active version for a specific complexity (or latest if none set)."""
    try:
        # Get the version to use (active or latest)
        version = version_manager.get_active_version(complexity)
        
        # Get metadata for this version
        metadata = version_manager.get_version_metadata(complexity, version)
        
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
    Get detailed metadata for a specific model version.
    """,
)
async def get_version_details(complexity: str, version: str):
    """Get metadata for a specific version."""
    metadata = version_manager.get_version_metadata(complexity, version)
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
    Endpoint to activate a model version for a specific complexity.
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
    request: dict = Body(..., example={"version": "v1_2024-11-28_01-00-00", "user": "admin@example.com"})
):
    """Activate a specific model version."""
    version = request.get("version")
    user = request.get("user", "system")
    
    if not version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Version is required"
        )
    
    # Verify version exists
    metadata = version_manager.get_version_metadata(complexity, version)
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
    Activate multiple model versions at once.
    Provide a dictionary mapping complexity to version.
    """,
)
async def activate_models_batch(
    request: dict = Body(..., example={
        "versions": {
            "Alta": "v1_2024-11-28_01-00-00",
            "Baja": "v2_2024-11-27_10-00-00"
        },
        "user": "admin@example.com"
    })
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
        metadata = version_manager.get_version_metadata(complexity, version)
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
