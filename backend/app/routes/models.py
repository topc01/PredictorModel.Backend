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
