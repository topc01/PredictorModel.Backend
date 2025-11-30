from fastapi import APIRouter, HTTPException, status, Depends
from app.predictor import predict
from app.utils.version import ComplexityMapper

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
  
  **Complejidades disponibles** (case-insensitive):
  
  | Label API | Nombre Real | Descripción |
  |-----------|-------------|-------------|
  | `baja` | Baja | Complejidad baja |
  | `media` | Media | Complejidad media |
  | `alta` | Alta | Complejidad alta |
  | `neonatologia` | Neonatología | Neonatología |
  | `pediatria` | Pediatría | Pediatría |
  | `intepediatrico` | Inte. Pediátrico | Intermedio Pediátrico |
  | `maternidad` | Maternidad | Maternidad |
  
  **Nota:** El API acepta mayúsculas y minúsculas (`alta`, `Alta`, `ALTA`), pero se recomienda usar minúsculas.
  
  **Validación:** Este endpoint usa `ComplexityMapper` para validar automáticamente el parámetro de complejidad.
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
async def predict_complexity(complexity: str = Depends(ComplexityMapper.is_valid_label)):
    """
    Realiza una predicción para una complejidad específica.
    
    Args:
        complexity: Label de la complejidad (baja, media, alta, neonatologia, pediatria, intepediatrico, maternidad)
    """
    try:
        # Parse API input to real complexity name
        real_complexity = ComplexityMapper.parse_from_api(complexity)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    prediction = predict(real_complexity)
    if prediction is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo realizar la predicción para la complejidad {complexity}."
        )
    return prediction