from fastapi import APIRouter, HTTPException, status, Body, File, UploadFile
import os
from app.utils.storage import check_bucket_access, get_bucket_info, storage_manager

router = APIRouter(
    tags=["Retrain"],
    responses={
        404: {"description": "No encontrado"},
        422: {"description": "Error de validación"},
    },
)


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Retrain the model",
    description="""
    Endpoint to trigger model retraining.
    """,
    responses={
        200: {
            "description": "Model retraining initiated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "retraining_started",
                        "message": "Model retraining has been initiated."
                    }
                }
            }
        },
        500: {
            "description": "Error initiating model retraining",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "message": "Failed to initiate model retraining."
                    }
                }
            }
        }
    },
)
async def retrain_endpoint():
    try:
        from app.retrain import retrain_model
        retrain_model()
        return {
            "status": "retraining_started",
            "message": "Model retraining has been initiated."
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": "Failed to initiate model retraining."
            }
        )


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    summary="Retrain the model",
    description="""
    Endpoint to trigger model retraining.
    """,
    responses={
        200: {
            "description": "Model retraining initiated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "retraining_started",
                        "message": "Model retraining has been initiated."
                    }
                }
            }
        },
        500: {
            "description": "Error initiating model retraining",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "message": "Failed to initiate model retraining."
                    }
                }
            }
        }
    },
)
async def retrain_endpoint():
    try:
        from app.retrain import retrain_model
        retrain_model()
        return {
            "status": "retraining_started",
            "message": "Model retraining has been initiated."
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": "Failed to initiate model retraining."
            }
        )


@router.get(
    "/all_models",
    status_code=status.HTTP_200_OK,
    summary="Get all retrained models",
    description="""
    Endpoint to retrieve all retrained models.
    """,
    responses={
        200: {
            "description": "List of all retrained models",
            "content": {
                "application/json": {
                    "example": {
                        "models": [
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
    try:
        from app.retrain.retrain import get_prophet_models
        from app.utils.complexities import ComplexityMapper
        
        # Get all complexity labels from the centralized mapper
        complexities = ComplexityMapper.get_all_labels()
        models = []
        for complexity in complexities:
            complexity_models = get_prophet_models(complexity)
            models.extend(complexity_models["models"])
        print("Retrieved models:", models)
        return {
            "models": models
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": "Failed to retrieve models."
            }
        )     