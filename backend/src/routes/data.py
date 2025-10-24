from fastapi import APIRouter, HTTPException, status, Body, File, UploadFile
from pydantic import BaseModel, Field, field_validator, ValidationError
from datetime import datetime
import pandas as pd
import io

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
        
@router.post(
    "/upload", 
    status_code=status.HTTP_200_OK,
    response_model=WeeklyDataResponse,
    summary="Subir archivo Excel con datos semanales",
    description="""
    Sube un archivo Excel (.xlsx) con datos semanales de todas las complejidades.
    
    **Formato del Excel:**
    
    El archivo debe contener una hoja con las siguientes columnas:
    - `complejidad`: Nombre de la complejidad (alta, baja, media, neonatología, pediatria)
    - `demanda_pacientes`: Cantidad de pacientes
    - `estancia (días)`: Promedio de estancia
    - `tipo de paciente_No Qx`: Proporción de pacientes no quirúrgicos (0-1)
    - `tipo de paciente Qx`: Proporción de pacientes quirúrgicos (0-1)
    - `tipo de ingreso_No Urgente`: Proporción de ingresos no urgentes (0-1)
    - `tipo de ingreso Urgente`: Proporción de ingresos urgentes (0-1)
    - `fecha ingreso completa`: Fecha en formato YYYY-MM-DD
    
    **Ejemplo de estructura:**
    
    | complejidad  | demanda_pacientes | estancia (días) | tipo de paciente_No Qx | ... |
    |--------------|-------------------|-----------------|------------------------|-----|
    | alta         | 50                | 5.2             | 0.6                    | ... |
    | baja         | 30                | 3.5             | 0.8                    | ... |
    | media        | 40                | 4.5             | 0.7                    | ... |
    | neonatología | 15                | 8.0             | 0.9                    | ... |
    | pediatria    | 25                | 4.0             | 0.75                   | ... |
    
    **Validaciones:**
    - Debe contener las 5 complejidades
    - Todos los campos son obligatorios
    - Formato de archivo: .xlsx o .xls
    """,
    responses={
        200: {
            "description": "Archivo procesado correctamente",
        },
        400: {
            "description": "Error al procesar el archivo - formato inválido o datos incorrectos",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Error al leer el archivo Excel: formato inválido"
                    }
                }
            }
        },
        422: {
            "description": "Error de validación de datos",
        }
    }
)
async def upload_data(
    file: UploadFile = File(..., description="Archivo Excel (.xlsx o .xls) con los datos semanales"),
):
    """
    Procesa un archivo Excel con datos semanales de todas las complejidades.
    
    El archivo debe contener una hoja con las 5 complejidades y sus respectivos datos.
    """
    # Validar extensión del archivo
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe ser un Excel (.xlsx o .xls)"
        )
    
    try:
        # Leer el contenido del archivo
        contents = await file.read()
        
        # Cargar el Excel con pandas
        df = pd.read_excel(io.BytesIO(contents))
        
        # Validar que tenga la columna 'complejidad'
        if 'complejidad' not in df.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo debe contener una columna 'complejidad'"
            )
        
        # Normalizar nombres de complejidades (minúsculas, sin tildes en comparación)
        df['complejidad'] = df['complejidad'].str.lower().str.strip()
        
        # Validar que estén las 5 complejidades requeridas
        required_complexities = {'alta', 'baja', 'media', 'neonatología', 'pediatria'}
        found_complexities = set(df['complejidad'].unique())
        
        # También aceptar sin tilde
        if 'neonatologia' in found_complexities:
            df.loc[df['complejidad'] == 'neonatologia', 'complejidad'] = 'neonatología'
            found_complexities = set(df['complejidad'].unique())
        
        missing = required_complexities - found_complexities
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Faltan las siguientes complejidades: {', '.join(missing)}"
            )
        
        # Validar que tenga todas las columnas necesarias
        required_columns = {
            'complejidad',
            'demanda_pacientes',
            'estancia (días)',
            'tipo de paciente_No Qx',
            'tipo de paciente Qx',
            'tipo de ingreso_No Urgente',
            'tipo de ingreso Urgente',
            'fecha ingreso completa'
        }
        
        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Faltan las siguientes columnas: {', '.join(missing_columns)}"
            )
        
        # Construir el objeto WeeklyDataRequest desde el DataFrame
        data_dict = {}
        
        for _, row in df.iterrows():
            complexity = row['complejidad']
            
            # Convertir fecha a string si es necesario
            fecha = row['fecha ingreso completa']
            if isinstance(fecha, pd.Timestamp):
                fecha = fecha.strftime('%Y-%m-%d')
            elif not isinstance(fecha, str):
                fecha = str(fecha)
            
            complexity_data = {
                'demanda_pacientes': float(row['demanda_pacientes']),
                'estancia (días)': float(row['estancia (días)']),
                'tipo de paciente_No Qx': float(row['tipo de paciente_No Qx']),
                'tipo de paciente Qx': float(row['tipo de paciente Qx']),
                'tipo de ingreso_No Urgente': float(row['tipo de ingreso_No Urgente']),
                'tipo de ingreso Urgente': float(row['tipo de ingreso Urgente']),
                'fecha ingreso completa': fecha
            }
            
            data_dict[complexity] = complexity_data
        
        # Validar con Pydantic
        try:
            validated_data = WeeklyDataRequest(**data_dict)
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Error de validación de datos: {e.errors()}"
            )
        
        # Retornar respuesta exitosa
        return WeeklyDataResponse(
            message="Archivo procesado correctamente",
            complejidades_recibidas=["alta", "baja", "media", "neonatología", "pediatria"],
            data=validated_data.model_dump(by_alias=True)
        )
        
    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo Excel está vacío"
        )
    except pd.errors.ParserError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error al leer el archivo Excel: formato inválido"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al procesar los datos: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al procesar el archivo: {str(e)}"
        )
