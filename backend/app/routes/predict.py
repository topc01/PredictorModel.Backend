from fastapi import APIRouter, HTTPException, status, Depends
from app.predictor import predict
from app.auth import get_current_user, require_role

router = APIRouter(
    tags=["Predict"],
    responses={
        404: {"description": "No encontrado"},
        422: {"description": "Error de validación"},
    },
)

@router.get(
  "/{complexity}", 
  summary="Realizar predicción", 
  description="""Realiza una predicción para una complejidad específica.
  
  Complejidades disponibles:
    - alta
    - media
    - baja
    - neonatologia
    - pediatria
  """,
  responses={
    200: {
      "description": "Predicción realizada correctamente",
      "content": {
        "application/json": {
          "example": {
            "complexity": "Alta",
            "predictions": {
              "demanda_pacientes": 50,
              "estancia_días": 5.2,
              "tipo_de_paciente_No_Qx": 30,
              "tipo_de_paciente_Qx": 20,
              "tipo_de_ingreso_No_Urgente": 45,
              "tipo_de_ingreso_Urgente": 15,
              "fecha_ingreso_completa": "2025-10-20"
            }
            }
        }
      }
    }
  }
)
async def predict_complexity(
    complexity: str,
    user: dict = Depends(require_role(["visualizador", "administrador"]))
):
    """
    Realiza una predicción para una complejidad específica.
    
    Args:
        complexity: Nombre de la complejidad (Alta, Media, Baja, Neonatología, Pediatría)
    """
    def parse(complexity: str) -> str:
        match complexity:
            case 'alta':
                return 'Alta'
            case 'media':
                return 'Media'
            case 'baja':
                return 'Baja'
            case 'neonatologia':
                return 'Neonatología'
            case 'pediatria':
                return 'Pediatría'
            case _:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Complejidad {complexity} inválida."
                )
    # Validar complejidad
    # valid_complexities = ['Alta', 'Media', 'Baja', 'Neonatología', 'Pediatría','Neonatologia', 'Pediatria']
    # if complexity not in valid_complexities:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail=f"Complejidad inválida. Valores permitidos: {', '.join(valid_complexities)}"
    #     )
    prediction = predict(parse(complexity))
    if prediction is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo realizar la predicción para la complejidad {complexity}."
        )
    return prediction