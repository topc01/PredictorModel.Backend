from pydantic import BaseModel, Field
from .WeeklyComplexityData import WeeklyComplexityData
import pandas as pd

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

    def to_df(self, by_alias: bool = True):
        rows = []
        for complexity_name, complexity_data in self.model_dump(by_alias=by_alias).items():
            row = {"Complejidad" if by_alias else "complejidad": complexity_name}
            row.update(complexity_data)
            rows.append(row)

        return pd.DataFrame(rows)
    
    def save_csv(self, filename: str, by_alias: bool = False):
        self.to_df(by_alias=by_alias).to_csv(filename, index=False)
    
    @staticmethod
    def from_df(df: pd.DataFrame):
        by_alias = df.columns.str.contains("Complejidad").any()
        complexity_map = {}
        for _, row in df.iterrows():
            key = row["Complejidad" if by_alias else "complejidad"]
            data = row.drop("Complejidad" if by_alias else "complejidad").to_dict()
            complexity_map[key] = WeeklyComplexityData(**data)
        return WeeklyData(**complexity_map)
      
    def to_json(self):
        return self.model_dump()
    
    @staticmethod
    def from_json(json: dict):
        return WeeklyData(**json)
 
    @staticmethod
    def from_csv(filename: str):
        return WeeklyData.from_df(pd.read_csv(filename))
    
    @staticmethod
    def example():
        return WeeklyData.from_json(WeeklyData.Config.json_schema_extra["example"])
    