from fastapi import APIRouter, HTTPException, status, Body, File, UploadFile
from pydantic import BaseModel
from typing import Optional
import os
from app.utils.storage import check_bucket_access, get_bucket_info, storage_manager

router = APIRouter(
    tags=["Storage"],
    responses={
        404: {"description": "No encontrado"},
        422: {"description": "Error de validación"},
    },
)


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Verificar conectividad con S3",
    description="""
    Verifica que el backend pueda conectarse correctamente a los buckets de S3.
    
    Este endpoint comprueba:
    - Acceso al bucket de archivos (S3_FILES_BUCKET)
    - Acceso al bucket de datos (S3_DATA_BUCKET)
    - Permisos IAM necesarios
    - Existencia de los buckets
    
    **Códigos de estado:**
    - 200: Todos los buckets son accesibles
    - 503: Uno o más buckets no son accesibles
    """,
    responses={
        200: {
            "description": "Todos los buckets de S3 son accesibles",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "message": "All S3 buckets are accessible",
                        "buckets": {
                            "files": {
                                "name": "predictor-model-prod-files",
                                "accessible": True,
                                "exists": True,
                                "region": "us-east-1"
                            },
                            "data": {
                                "name": "predictor-model-prod-data",
                                "accessible": True,
                                "exists": True,
                                "region": "us-east-1"
                            }
                        }
                    }
                }
            }
        },
        503: {
            "description": "Uno o más buckets no son accesibles",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "message": "Some S3 buckets are not accessible",
                        "buckets": {
                            "files": {
                                "name": "predictor-model-prod-files",
                                "accessible": False,
                                "exists": True,
                                "error": "Access denied - check IAM permissions"
                            }
                        }
                    }
                }
            }
        }
    }
)
async def storage_health_check():
    """
    Verifica la conectividad y acceso a los buckets de S3.
    
    Este endpoint es útil para:
    - Verificar la configuración de IAM
    - Comprobar que los buckets existen
    - Diagnosticar problemas de conectividad
    - Monitoreo de infraestructura
    """
    # Get bucket names from environment variables
    files_bucket = os.getenv('S3_FILES_BUCKET')
    data_bucket = os.getenv('S3_DATA_BUCKET')
    storage_type = storage_manager.storage_type
    
    # Check if environment variables are set
    if not files_bucket or not data_bucket:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "message": "S3 bucket configuration missing",
                "error": "S3_FILES_BUCKET or S3_DATA_BUCKET environment variables not set"
            }
        )
    
    # Check access to both buckets
    files_check = check_bucket_access(files_bucket)
    data_check = check_bucket_access(data_bucket)
    
    # Get additional bucket info if accessible
    files_info = get_bucket_info(files_bucket) if files_check['accessible'] else None
    data_info = get_bucket_info(data_bucket) if data_check['accessible'] else None
    
    # Build response
    response = {
        "buckets": {
            "files": {
                "name": files_bucket,
                "accessible": files_check['accessible'],
                "exists": files_check['exists'],
            },
            "data": {
                "name": data_bucket,
                "accessible": data_check['accessible'],
                "exists": data_check['exists'],
            }
        },
        "using_storage": storage_type,
        "status": "",
        "message": "",
    }
    
    # Add errors if present
    if files_check['error']:
        response["buckets"]["files"]["error"] = files_check['error']
    if data_check['error']:
        response["buckets"]["data"]["error"] = data_check['error']
    
    # Add region info if available
    if files_info:
        response["buckets"]["files"]["region"] = files_info['region']
    if data_info:
        response["buckets"]["data"]["region"] = data_info['region']
    
    # Determine overall health status
    all_accessible = files_check['accessible'] and data_check['accessible']
    
    if all_accessible:
        response["status"] = "healthy"
        response["message"] = "All S3 buckets are accessible"
        return response
    else:
        response["status"] = "unhealthy"
        response["message"] = "Some S3 buckets are not accessible"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response
        )

class WeekDeleteRequest(BaseModel):
    filename: str = "dataset.csv"
    semana_año: str = "2025-31"
    column_name: Optional[str] = "semana_año"

@router.delete(
    "/storage/week",
    status_code=status.HTTP_200_OK,
    summary="Eliminar una semana de un CSV",
    description="Elimina las filas que correspondan a `semana_año` dentro del CSV indicado (por defecto `dataset.csv`).",
)
async def delete_week(payload: WeekDeleteRequest = Body(...)):
    try:
        removed = storage_manager.remove_week_from_file(payload.filename, payload.semana_año, payload.column_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": str(e)})
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"message": str(e)})
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"message": str(e)})

    return {"filename": payload.filename, "semana_año": payload.semana_año, "rows_removed": removed}

class LastRowsDeleteRequest(BaseModel):
    filename: str = "dataset.csv"
    n_rows: int = 1

@router.delete(
    "/storage/last-rows",
    status_code=status.HTTP_200_OK,
    summary="Eliminar las últimas n filas de un CSV",
    description="Elimina las últimas `n_rows` filas del CSV indicado (por defecto `dataset.csv`). CSV se encuentra ordenado según semana_año.",
)
async def delete_last_rows(payload: LastRowsDeleteRequest = Body(...)):
    try:
        removed = storage_manager.remove_last_row_from_file(payload.filename, payload.n_rows)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": str(e)})
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"message": str(e)})
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"message": str(e)})

    return {"filename": payload.filename, "rows_removed": removed}