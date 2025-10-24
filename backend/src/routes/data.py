from fastapi import APIRouter, HTTPException, status, Body
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Literal

router = APIRouter(
    tags=["Data"],
    responses={
        404: {"description": "No encontrado"},
        422: {"description": "Error de validación"},
    },
)

class WeeklyComplexityData(BaseModel):
    """
    Datos semanales para una complejidad específica.
    
    Contiene información histórica de la semana anterior para realizar predicciones.
    """
    demanda_pacientes: float = Field(
        ..., 
        description="Cantidad real de pacientes de la semana pasada",
        gt=0,
        examples=[50, 75, 100]
    )
    estancia__días_: float = Field(
        ..., 
        alias='estancia (días)', 
        description="Promedio de días de estancia hospitalaria de la semana pasada",
        gt=0,
        examples=[5.2, 7.8, 3.5]
    )
    tipo_de_paciente_No_Qx: float = Field(
        ..., 
        alias='tipo de paciente_No Qx', 
        description="Proporción de pacientes no quirúrgicos (0-1)",
        ge=0,
        le=1,
        examples=[0.6, 0.45, 0.7]
    )
    tipo_de_paciente_Qx: float = Field(
        ..., 
        alias='tipo de paciente Qx', 
        description="Proporción de pacientes quirúrgicos (0-1)",
        ge=0,
        le=1,
        examples=[0.4, 0.55, 0.3]
    )
    tipo_de_ingreso_No_Urgente: float = Field(
        ..., 
        alias='tipo de ingreso_No Urgente', 
        description="Proporción de ingresos no urgentes/programados (0-1)",
        ge=0,
        le=1,
        examples=[0.7, 0.65, 0.8]
    )
    tipo_de_ingreso_Urgente: float = Field(
        ..., 
        alias='tipo de ingreso Urgente', 
        description="Proporción de ingresos urgentes (0-1)",
        ge=0,
        le=1,
        examples=[0.3, 0.35, 0.2]
    )
    fecha_ingreso_completa: str = Field(
        ..., 
        alias='fecha ingreso completa', 
        description="Fecha de ingreso de los datos en formato ISO (YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS)",
        examples=["2025-10-20", "2025-10-20T00:00:00"]
    )
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "demanda_pacientes": 50,
                "estancia (días)": 5.2,
                "tipo de paciente_No Qx": 0.6,
                "tipo de paciente Qx": 0.4,
                "tipo de ingreso_No Urgente": 0.7,
                "tipo de ingreso Urgente": 0.3,
                "fecha ingreso completa": "2025-10-20"
            }
        }
    
    @field_validator('fecha_ingreso_completa')
    @classmethod
    def validate_fecha(cls, v: str) -> str:
        """Valida que la fecha tenga un formato válido"""
        try:
            # Intenta parsear la fecha para verificar que es válida
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError(f"Formato de fecha inválido: {v}. Use formato ISO (YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS)")

class WeeklyDataRequest(BaseModel):
    """
    Solicitud de datos semanales para todas las complejidades hospitalarias.
    
    Este modelo agrupa los datos históricos de las 5 complejidades principales
    para realizar predicciones de demanda hospitalaria.
    """
    alta: WeeklyComplexityData = Field(
        ..., 
        description="Datos de complejidad alta"
    )
    baja: WeeklyComplexityData = Field(
        ..., 
        description="Datos de complejidad baja"
    )
    media: WeeklyComplexityData = Field(
        ..., 
        description="Datos de complejidad media"
    )
    neonatologia: WeeklyComplexityData = Field(
        ..., 
        alias='neonatología',
        description="Datos de neonatología"
    )
    pediatria: WeeklyComplexityData = Field(
        ..., 
        description="Datos de pediatría"
    )
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "alta": {
                    "demanda_pacientes": 50,
                    "estancia (días)": 5.2,
                    "tipo de paciente_No Qx": 0.6,
                    "tipo de paciente Qx": 0.4,
                    "tipo de ingreso_No Urgente": 0.7,
                    "tipo de ingreso Urgente": 0.3,
                    "fecha ingreso completa": "2025-10-20"
                },
                "baja": {
                    "demanda_pacientes": 30,
                    "estancia (días)": 3.5,
                    "tipo de paciente_No Qx": 0.8,
                    "tipo de paciente Qx": 0.2,
                    "tipo de ingreso_No Urgente": 0.85,
                    "tipo de ingreso Urgente": 0.15,
                    "fecha ingreso completa": "2025-10-20"
                },
                "media": {
                    "demanda_pacientes": 40,
                    "estancia (días)": 4.5,
                    "tipo de paciente_No Qx": 0.7,
                    "tipo de paciente Qx": 0.3,
                    "tipo de ingreso_No Urgente": 0.75,
                    "tipo de ingreso Urgente": 0.25,
                    "fecha ingreso completa": "2025-10-20"
                },
                "neonatología": {
                    "demanda_pacientes": 15,
                    "estancia (días)": 8.0,
                    "tipo de paciente_No Qx": 0.9,
                    "tipo de paciente Qx": 0.1,
                    "tipo de ingreso_No Urgente": 0.5,
                    "tipo de ingreso Urgente": 0.5,
                    "fecha ingreso completa": "2025-10-20"
                },
                "pediatria": {
                    "demanda_pacientes": 25,
                    "estancia (días)": 4.0,
                    "tipo de paciente_No Qx": 0.75,
                    "tipo de paciente Qx": 0.25,
                    "tipo de ingreso_No Urgente": 0.6,
                    "tipo de ingreso Urgente": 0.4,
                    "fecha ingreso completa": "2025-10-20"
                }
            }
        }
  
class WeeklyDataResponse(BaseModel):
    """Respuesta del endpoint de envío de datos"""
    message: str = Field(..., description="Mensaje de confirmación")
    complejidades_recibidas: list[str] = Field(..., description="Lista de complejidades procesadas")
    data: dict = Field(..., description="Datos recibidos")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Datos recibidos correctamente",
                "complejidades_recibidas": ["alta", "baja", "media", "neonatología", "pediatria"],
                "data": {
                    "alta": {
                        "demanda_pacientes": 50,
                        "estancia (días)": 5.2,
                        "tipo de paciente_No Qx": 0.6,
                        "tipo de paciente Qx": 0.4,
                        "tipo de ingreso_No Urgente": 0.7,
                        "tipo de ingreso Urgente": 0.3,
                        "fecha ingreso completa": "2025-10-20"
                    }
                }
            }
        }

@router.post(
    "/send", 
    status_code=status.HTTP_200_OK,
    response_model=WeeklyDataResponse,
    summary="Enviar datos semanales de complejidades",
    description="""
    Recibe datos históricos de la semana anterior para las 5 complejidades hospitalarias.
    
    **Complejidades requeridas:**
    - `alta`: Complejidad alta
    - `baja`: Complejidad baja  
    - `media`: Complejidad media
    - `neonatología`: Neonatología
    - `pediatria`: Pediatría
    
    **Cada complejidad debe incluir:**
    - `demanda_pacientes`: Cantidad real de pacientes (> 0)
    - `estancia (días)`: Promedio de días de estancia (> 0)
    - `tipo de paciente_No Qx`: Proporción no quirúrgicos (0-1)
    - `tipo de paciente Qx`: Proporción quirúrgicos (0-1)
    - `tipo de ingreso_No Urgente`: Proporción ingresos programados (0-1)
    - `tipo de ingreso Urgente`: Proporción ingresos urgentes (0-1)
    - `fecha ingreso completa`: Fecha en formato ISO (YYYY-MM-DD)
    
    **Validaciones automáticas:**
    - Todas las complejidades deben estar presentes
    - Todos los campos son obligatorios
    - Las proporciones deben estar entre 0 y 1
    - Las cantidades deben ser mayores que 0
    - La fecha debe tener formato válido
    """,
    responses={
        200: {
            "description": "Datos recibidos y validados correctamente",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Datos recibidos correctamente",
                        "complejidades_recibidas": ["alta", "baja", "media", "neonatología", "pediatria"],
                        "data": {
                            "alta": {
                                "demanda_pacientes": 50,
                                "estancia (días)": 5.2,
                                "tipo de paciente_No Qx": 0.6,
                                "tipo de paciente Qx": 0.4,
                                "tipo de ingreso_No Urgente": 0.7,
                                "tipo de ingreso Urgente": 0.3,
                                "fecha ingreso completa": "2025-10-20"
                            }
                        }
                    }
                }
            }
        },
        422: {
            "description": "Error de validación - faltan datos o formato incorrecto",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "type": "missing",
                                "loc": ["body", "alta"],
                                "msg": "Field required"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def post_data(
    data: WeeklyDataRequest = Body(
        ...,
        openapi_examples={
            "ejemplo_completo": {
                "summary": "Ejemplo con datos de todas las complejidades",
                "description": "Ejemplo completo con datos realistas para las 5 complejidades",
                "value": {
                    "alta": {
                        "demanda_pacientes": 50,
                        "estancia (días)": 5.2,
                        "tipo de paciente_No Qx": 0.6,
                        "tipo de paciente Qx": 0.4,
                        "tipo de ingreso_No Urgente": 0.7,
                        "tipo de ingreso Urgente": 0.3,
                        "fecha ingreso completa": "2025-10-20"
                    },
                    "baja": {
                        "demanda_pacientes": 30,
                        "estancia (días)": 3.5,
                        "tipo de paciente_No Qx": 0.8,
                        "tipo de paciente Qx": 0.2,
                        "tipo de ingreso_No Urgente": 0.85,
                        "tipo de ingreso Urgente": 0.15,
                        "fecha ingreso completa": "2025-10-20"
                    },
                    "media": {
                        "demanda_pacientes": 40,
                        "estancia (días)": 4.5,
                        "tipo de paciente_No Qx": 0.7,
                        "tipo de paciente Qx": 0.3,
                        "tipo de ingreso_No Urgente": 0.75,
                        "tipo de ingreso Urgente": 0.25,
                        "fecha ingreso completa": "2025-10-20"
                    },
                    "neonatología": {
                        "demanda_pacientes": 15,
                        "estancia (días)": 8.0,
                        "tipo de paciente_No Qx": 0.9,
                        "tipo de paciente Qx": 0.1,
                        "tipo de ingreso_No Urgente": 0.5,
                        "tipo de ingreso Urgente": 0.5,
                        "fecha ingreso completa": "2025-10-20"
                    },
                    "pediatria": {
                        "demanda_pacientes": 25,
                        "estancia (días)": 4.0,
                        "tipo de paciente_No Qx": 0.75,
                        "tipo de paciente Qx": 0.25,
                        "tipo de ingreso_No Urgente": 0.6,
                        "tipo de ingreso Urgente": 0.4,
                        "fecha ingreso completa": "2025-10-20"
                    }
                }
            }
        }
    )
):
    """
    Procesa y valida datos semanales de todas las complejidades hospitalarias.
    
    Este endpoint recibe datos históricos de la semana anterior para las 5 complejidades
    y los valida antes de procesarlos para predicciones futuras.
    """
    try:
        # Aquí puedes procesar los datos recibidos
        return WeeklyDataResponse(
            message="Datos recibidos correctamente",
            complejidades_recibidas=["alta", "baja", "media", "neonatología", "pediatria"],
            data=data.model_dump(by_alias=True)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error procesando los datos: {str(e)}"
        )