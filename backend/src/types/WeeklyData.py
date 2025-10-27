from pydantic import BaseModel, Field
from .WeeklyComplexityData import WeeklyComplexityData

class WeeklyData(BaseModel):
    """
    Solicitud de datos semanales para todas las complejidades hospitalarias.
    
    Este modelo agrupa los datos históricos de las 5 complejidades principales
    para realizar predicciones de demanda hospitalaria.
    """
    alta: WeeklyComplexityData = Field(
        ...,
        alias='Alta',
        description="Datos de complejidad alta"
    )
    baja: WeeklyComplexityData = Field(
        ..., 
        alias='Baja',
        description="Datos de complejidad baja"
    )
    media: WeeklyComplexityData = Field(
        ..., 
        alias='Media',
        description="Datos de complejidad media"
    )
    neonatologia: WeeklyComplexityData = Field(
        ..., 
        alias='Neonatología',
        description="Datos de neonatología"
    )
    pediatria: WeeklyComplexityData = Field(
        ..., 
        alias='Pediatría',
        description="Datos de pediatría"
    )
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "Alta": {
                    "Demanda pacientes": 50,
                    "Estancia (días promedio)": 5.2,
                    "Pacientes no Qx": 30,
                    "Pacientes Qx": 20,
                    "Ingresos no urgentes": 45,
                    "Ingresos urgentes": 15,
                    "Fecha ingreso": "2025-10-20"
                },
                "Baja": {
                    "Demanda pacientes": 30,
                    "Estancia (días promedio)": 3.8,
                    "Pacientes no Qx": 24,
                    "Pacientes Qx": 6,
                    "Ingresos no urgentes": 25,
                    "Ingresos urgentes": 5,
                    "Fecha ingreso": "2025-10-20"
                },
                "Media": {
                    "Demanda pacientes": 40,
                    "Estancia (días promedio)": 4,
                    "Pacientes no Qx": 40,
                    "Pacientes Qx": 10,
                    "Ingresos no urgentes": 75,
                    "Ingresos urgentes": 25,
                    "Fecha ingreso": "2025-10-20"
                },
                "Neonatología": {
                    "Demanda pacientes": 15,
                    "Estancia (días promedio)": 8,
                    "Pacientes no Qx": 9,
                    "Pacientes Qx": 1,
                    "Ingresos no urgentes": 5,
                    "Ingresos urgentes": 5,
                    "Fecha ingreso": "2025-10-20"
                },
                "Pediatría": {
                    "Demanda pacientes": 25,
                    "Estancia (días promedio)": 4,
                    "Pacientes no Qx": 75,
                    "Pacientes Qx": 25,
                    "Ingresos no urgentes": 6,
                    "Ingresos urgentes": 4,
                    "Fecha ingreso": "2025-10-20"
                }
            }
        }