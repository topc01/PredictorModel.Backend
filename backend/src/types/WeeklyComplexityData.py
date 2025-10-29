from pydantic import BaseModel, Field, field_validator, ValidationError
from datetime import datetime

class WeeklyComplexityData(BaseModel):
    """
    Datos semanales para una complejidad específica.
    
    Contiene información histórica de la semana anterior para realizar predicciones.
    """
    demanda_pacientes: int = Field(
        ...,
        alias='Demanda pacientes',
        description="Cantidad real de pacientes de la semana pasada",
        gt=0,
        examples=[50, 75, 100]
    )
    estancia: float = Field(
        ..., 
        alias='Estancia (días promedio)', 
        description="Promedio de días de estancia hospitalaria de la semana pasada",
        gt=0,
        examples=[5.2, 7.5, 3.8]
    )
    pacientes_no_Qx: int = Field(
        ..., 
        alias='Pacientes no Qx', 
        description="Cantidad de pacientes no quirúrgicos",
        ge=0,
        examples=[30, 20, 40]
    )
    pacientes_Qx: int = Field(
        ..., 
        alias='Pacientes Qx', 
        description="Cantidad de pacientes quirúrgicos",
        ge=0,
        examples=[20, 30, 10]
    )
    ingresos_no_urgentes: int = Field(
        ..., 
        alias='Ingresos no urgentes', 
        description="Cantidad de ingresos no urgentes/programados",
        ge=0,
        examples=[45, 25, 55]
    )
    ingresos_urgentes: int = Field(
        ..., 
        alias='Ingresos urgentes', 
        description="Cantidad de ingresos urgentes",
        ge=0,
        examples=[15, 5, 25]
    )
    fecha_ingreso: str = Field(
        ..., 
        alias='Fecha ingreso', 
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
    
    @field_validator('fecha_ingreso')
    @classmethod
    def validate_fecha(cls, v: str) -> str:
        """Valida que la fecha tenga un formato válido"""
        try:
            # Intenta parsear la fecha para verificar que es válida
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError(f"Formato de fecha inválido: {v}. Use formato ISO (YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS)")
