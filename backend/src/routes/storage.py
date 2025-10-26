from fastapi import APIRouter, HTTPException, status, Body, File, UploadFile
import os
from src.utils.storage import check_bucket_access, get_bucket_info

router = APIRouter(
    tags=["Storage"],
    responses={
        404: {"description": "No encontrado"},
        422: {"description": "Error de validación"},
    },
)


@router.get(
    "/storage/health",
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