from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Literal

router = APIRouter()

class WeeklyComplexityData(BaseModel):
    """Datos semanales para una complejidad específica"""
    demanda_pacientes: float = Field(..., description="Cantidad real de pacientes de la semana pasada")
    estancia__días_: float = Field(..., alias='estancia (días)', description="Promedio de estancia de la semana pasada")
    tipo_de_paciente_No_Qx: float = Field(..., alias='tipo de paciente_No Qx', description="Tipo de paciente: No quirúrgico")
    tipo_de_paciente_Qx: float = Field(..., alias='tipo de paciente Qx', description="Tipo de paciente: Quirúrgico")
    tipo_de_ingreso_No_Urgente: float = Field(..., alias='tipo de ingreso_No Urgente', description="Tipo de ingreso: No urgente")
    tipo_de_ingreso_Urgente: float = Field(..., alias='tipo de ingreso Urgente', description="Tipo de ingreso: Urgente")
    fecha_ingreso_completa: str = Field(..., alias='fecha ingreso completa', description="Fecha de ingreso de los datos")
    
    class Config:
        populate_by_name = True
    
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
    """Datos semanales para todas las complejidades"""
    alta: WeeklyComplexityData
    baja: WeeklyComplexityData
    media: WeeklyComplexityData
    neonatologia: WeeklyComplexityData = Field(..., alias='neonatología')
    pediatria: WeeklyComplexityData
    
    class Config:
        populate_by_name = True
  
@router.post("/send", status_code=status.HTTP_200_OK)
async def post_data(data: WeeklyDataRequest):
    """
    Endpoint para recibir datos semanales de todas las complejidades.
    
    Requiere datos para: alta, baja, media, neonatología, pediatria
    
    Cada complejidad debe incluir:
    - demanda_pacientes: Cantidad real de pacientes de la semana pasada
    - estancia (días): Promedio de estancia de la semana pasada
    - tipo de paciente_No Qx: Proporción de pacientes no quirúrgicos
    - tipo de paciente Qx: Proporción de pacientes quirúrgicos
    - tipo de ingreso_No Urgente: Proporción de ingresos no urgentes
    - tipo de ingreso Urgente: Proporción de ingresos urgentes
    - fecha ingreso completa: Fecha de ingreso de los datos
    """
    try:
        # Aquí puedes procesar los datos recibidos
        return {
            "message": "Datos recibidos correctamente",
            "complejidades_recibidas": ["alta", "baja", "media", "neonatología", "pediatria"],
            "data": data.model_dump(by_alias=True)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error procesando los datos: {str(e)}"
        )