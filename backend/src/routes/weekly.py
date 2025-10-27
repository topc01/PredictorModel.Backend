from fastapi import APIRouter, HTTPException, status, Body, File, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator, ValidationError
from datetime import datetime
import pandas as pd
import io
from ..utils.storage import storage_manager
from ..pipeline import preparar_datos_prediccion_global
from ..types import WeeklyData

router = APIRouter(
    tags=["Weekly Data"],
    responses={
        404: {"description": "No encontrado"},
        422: {"description": "Error de validación"},
    },
)

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
                        "estancia (días)": 5,
                        "tipo de paciente_No Qx": 30,
                        "tipo de paciente Qx": 20,
                        "tipo de ingreso_No Urgente": 45,
                        "tipo de ingreso Urgente": 15,
                        "fecha ingreso completa": "2025-10-20"
                    }
                }
            }
        }

@router.post(
    "/send", 
    status_code=status.HTTP_200_OK,
    summary="Enviar datos semanales de complejidades",
    description="""
    Recibe datos históricos de la semana anterior para las 5 complejidades hospitalarias.
    
    Complejidades requeridas:
    - Alta: Complejidad alta
    - Baja: Complejidad baja  
    - Media: Complejidad media
    - Neonatología: Neonatología
    - Pediatría: Pediatría
    
    Cada complejidad debe incluir:
    - Demanda pacientes: Cantidad de pacientes
    - Estancia (días promedio): Promedio de estancia
    - Pacientes no Qx: Cantidad de pacientes no quirúrgicos
    - Pacientes Qx: Cantidad de pacientes quirúrgicos
    - Ingresos no urgentes: Cantidad de ingresos no urgentes
    - Ingresos urgentes: Cantidad de ingresos urgentes
    - Fecha ingreso: Fecha en formato YYYY-MM-DD
    
    Validaciones automáticas:
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
                                "estancia (días)": 5,
                                "tipo de paciente_No Qx": 6,
                                "tipo de paciente Qx": 20,
                                "tipo de ingreso_No Urgente": 45,
                                "tipo de ingreso Urgente": 15,
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
    data: WeeklyData = Body(
        ...,
        description="Datos semanales de todas las complejidades hospitalarias"
    )
):
    """
    Procesa y valida datos semanales de todas las complejidades hospitalarias.
    
    Este endpoint recibe datos históricos de la semana anterior para las 5 complejidades
    y los valida antes de procesarlos para predicciones futuras.
    """
    try:
        
        data.save_csv("data/weekly.csv")
        
        # preparar_datos_prediccion_global(data.model_dump())

        return {
            "message": "Datos recibidos correctamente",
        }
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error de validación de datos: {e.errors()}"
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
        
@router.post(
    "/upload", 
    status_code=status.HTTP_200_OK,
    summary="Subir archivo Excel con datos semanales",
    description="""
    Sube un archivo Excel (.xlsx) con datos semanales de todas las complejidades.
    
    Formato del Excel:
    
    El archivo debe contener una hoja con las siguientes columnas:
    - Complejidad: Nombre de la complejidad (Alta, Baja, Media, Neonatología, Pediatría)
    - Demanda pacientes: Cantidad de pacientes
    - Estancia (días promedio): Promedio de estancia
    - Pacientes no Qx: Cantidad de pacientes no quirúrgicos
    - Pacientes Qx: Cantidad de pacientes quirúrgicos
    - Ingresos no urgentes: Cantidad de ingresos no urgentes
    - Ingresos urgentes: Cantidad de ingresos urgentes
    - Fecha ingreso: Fecha en formato YYYY-MM-DD
    
    Ejemplo de estructura:
    
    | Complejidad  | Demanda pacientes | Estancia (días promedio) | Pacientes no Qx | Pacientes Qx | Ingresos no urgentes | Ingresos urgentes | Fecha ingreso |
    |--------------|-------------------|--------------------------|-----------------|--------------|----------------------|-------------------|---------------|
    | Alta         | 50                | 5.2                      | 30              | 20           | 45                   | 15                | "2025-10-20"  |
    | Baja         | 30                | 3.8                      | 24              | 6            | 25                   | 5                 | "2025-10-20"  |
    | Media        | 40                | 4                        | 40              | 10           | 75                   | 25                | "2025-10-20"  |
    | Neonatología | 15                | 8                        | 9               | 1            | 5                    | 5                 | "2025-10-20"  |
    | Pediatría    | 25                | 4                        | 75              | 25           | 6                    | 4                 | "2025-10-20"  |
    
    Validaciones:
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
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se proporcionó un nombre de archivo"
        )
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe ser un Excel (.xlsx o .xls)"
        )
    
    try:
        contents = await file.read()
        
        df = pd.read_excel(io.BytesIO(contents))
        
        data = WeeklyData.from_df(df)
        
        data.save_csv("data/weekly.csv")
        
        # preparar_datos_prediccion_global(data.model_dump())
        
        return {
            "message": "Archivo procesado correctamente"
        }
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error de validación de datos: {e.errors()}"
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

@router.get(
    "/template",
    summary="Descargar plantilla Excel",
    description="""
    Descarga una plantilla de Excel con el formato correcto para subir datos.
    
    La plantilla incluye:
    - Todas las columnas requeridas
    - Filas de ejemplo para cada complejidad
    - Formato correcto de datos
    
    Puedes usar esta plantilla como base para subir tus propios datos.
    """,
    responses={
        200: {
            "description": "Plantilla Excel descargada correctamente",
            "content": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}
            }
        }
    }
)
async def download_template():
    """
    Genera y descarga una plantilla de Excel con el formato correcto.
    """
    
    df = WeeklyData.example().to_df()
    
    # Crear archivo Excel en memoria
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: # type: ignore[arg-type]
        df.to_excel(writer, index=False, sheet_name='Datos Semanales')
        
        worksheet = writer.sheets['Datos Semanales']
        
        # Ajustar ancho de columnas
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    
    # Retornar como respuesta de descarga
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=template_datos_semanales.xlsx"
        }
    )
    
@router.get(
  "/last-date",
  summary="Obtener la última fecha de datos semanales",
  description="""
  Obtiene la última fecha de datos semanales procesados.
  """,
  responses={
    200: {
      "description": "Última fecha de datos semanales",
      "content": {
        "application/json": {
          "example": {
            "last_date": "2025-10-20"
          }
        }
      }
    },
    404: {
      "description": "No se encontraron datos semanales",
      "content": {
        "application/json": {
          "example": {
            "detail": "No se encontraron datos semanales"
          }
        }
      }
    }
  }
)
async def get_last_date():
  """
  Obtiene la última fecha de datos semanales procesados.
  """
  try:
    data = WeeklyData.from_csv("data/weekly.csv")
    df = data.to_df(by_alias=False)
    last_date = df["fecha_ingreso"].max()
  except Exception as e:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=f"No se encontraron datos semanales: {e}"
    )
  return {"last_date": last_date}