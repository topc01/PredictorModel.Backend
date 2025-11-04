"""
Pipeline routes for data cleaning and processing.

These endpoints handle the initial Excel processing and data cleaning pipeline.
"""

from fastapi import APIRouter, HTTPException, status, File, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, Optional
import pandas as pd
import io
import zipfile
from datetime import datetime
import os
from ..pipeline import procesar_excel_completo
from ..utils.storage import storage_manager


router = APIRouter(
    tags=["Data"],
    responses={
        404: {"description": "No encontrado"},
        400: {"description": "Error de procesamiento"},
        422: {"description": "Error de validación"},
    },
)


class PipelineProcessResponse(BaseModel):
    """Respuesta del procesamiento del pipeline."""
    message: str = Field(..., description="Mensaje de resultado")
    # complejidades_procesadas: Dict[str, str] = Field(
    #     ..., 
    #     description="Diccionario con complejidades procesadas y su estado"
    # )
    # archivos_generados: Dict[str, str] = Field(
    #     ..., 
    #     description="Rutas de los archivos CSV generados"
    # )
    # estadisticas: Dict[str, Dict[str, int]] = Field(
    #     ..., 
    #     description="Estadísticas de cada complejidad procesada"
    # )
    timestamp: str = Field(..., description="Timestamp del procesamiento")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Archivo procesado exitosamente",
                "complejidades_procesadas": {
                    "Alta": "Procesada exitosamente",
                    "Baja": "Procesada exitosamente",
                    "Media": "Procesada exitosamente",
                    "Neonatología": "Datos insuficientes",
                    "Pediatría": "Procesada exitosamente"
                },
                "archivos_generados": {
                    "Alta": "./data/Alta.csv",
                    "Baja": "./data/Baja.csv",
                    "Media": "./data/Media.csv",
                    "Pediatría": "./data/Pediatría.csv"
                },
                "estadisticas": {
                    "Alta": {"filas": 120, "columnas": 18},
                    "Baja": {"filas": 98, "columnas": 18}
                },
                "timestamp": "2025-10-26T12:30:45"
            }
        }


@router.post(
    "/process-excel",
    status_code=status.HTTP_200_OK,
    response_model=PipelineProcessResponse,
    summary="Procesar archivo Excel inicial",
    description="""
    Procesa un archivo Excel con datos hospitalarios crudos y genera datasets limpios por complejidad.
    
    Requisitos del archivo Excel:
    - Debe tener al menos 3 hojas
    - Hoja 0: Datos principales de pacientes con columnas:
        - Servicio Ingreso (Código)
        - Fecha Ingreso Completa
        - Estancia (Días)
        - Tipo de Paciente
        - Tipo de Ingreso
        - Y otras columnas de metadata
    - Hoja 2: Datos de servicios/complejidad con columnas:
        - UO trat. (código de unidad)
        - Complejidad
    
    Proceso realizado:
    1. Limpieza y normalización de datos
    2. Merge de hojas de datos
    3. Creación de features temporales (semana, mes, estación)
    4. One-hot encoding de variables categóricas
    5. Agrupación semanal
    6. Creación de lags (1, 2, 3, 4, 10, 52 semanas)
    7. Generación de CSV por complejidad
    
    Complejidades procesadas:
    - Alta
    - Media
    - Baja
    - Neonatología
    - Pediatría
    
    Nota: Las complejidades con menos de 55 semanas de datos no serán procesadas.
    """,
    responses={
        200: {
            "description": "Archivo procesado exitosamente",
        },
        400: {
            "description": "Error al procesar el archivo",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "El archivo debe tener al menos 3 hojas"
                    }
                }
            }
        }
    }
)
async def process_excel(
    file: UploadFile = File(
        ..., 
        description="Archivo Excel (.xlsx o .xls) con datos hospitalarios crudos"
    )
):
    """
    Procesa un archivo Excel inicial con datos hospitalarios.
    
    Este endpoint ejecuta el pipeline completo de limpieza y genera
    archivos CSV por complejidad listos para entrenamiento de modelos.
    """
    # Validar archivo
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
        # Leer archivo
        contents = await file.read()
        excel_file = io.BytesIO(contents)
        
        # Procesar Excel completo
        procesar_excel_completo(excel_file)
        
        return PipelineProcessResponse(
            message="Archivo procesado exitosamente",
            timestamp=datetime.now().isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al procesar el archivo: {str(e)}"
        )


# @router.get(
#     "/download/{complejidad}",
#     summary="Descargar CSV de complejidad",
#     description="""
#     Descarga el CSV procesado de una complejidad específica.
    
#     **Complejidades disponibles:**
#     - `Alta`
#     - `Media`
#     - `Baja`
#     - `Neonatología`
#     - `Pediatría`
    
#     El archivo debe haber sido procesado previamente mediante el endpoint `/pipeline/process-excel`.
#     """,
#     responses={
#         200: {
#             "description": "CSV descargado correctamente",
#             "content": {
#                 "text/csv": {}
#             }
#         },
#         404: {
#             "description": "Archivo no encontrado",
#             "content": {
#                 "application/json": {
#                     "example": {
#                         "detail": "No se encontró el archivo para la complejidad: Alta"
#                     }
#                 }
#             }
#         }
#     }
# )
# async def download_complejidad_csv(complejidad: str):
#     """
#     Descarga el CSV de una complejidad específica.
    
#     Args:
#         complejidad: Nombre de la complejidad (Alta, Media, Baja, Neonatología, Pediatría)
#     """
#     # Validar complejidad
#     complejidades_validas = ['Alta', 'Media', 'Baja', 'Neonatología', 'Pediatría']
#     if complejidad not in complejidades_validas:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"Complejidad inválida. Valores permitidos: {', '.join(complejidades_validas)}"
#         )
    
#     filename = f"{complejidad}.csv"
    
#     try:
#         # Cargar CSV
#         df = storage_manager.load_csv(filename)
        
#         # Convertir a CSV en memoria
#         csv_buffer = io.StringIO()
#         df.to_csv(csv_buffer, index=False)
#         csv_buffer.seek(0)
        
#         # Retornar como descarga
#         return StreamingResponse(
#             io.BytesIO(csv_buffer.getvalue().encode()),
#             media_type="text/csv",
#             headers={
#                 "Content-Disposition": f"attachment; filename={filename}"
#             }
#         )
        
#     except FileNotFoundError:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"No se encontró el archivo para la complejidad: {complejidad}. "
#                    "Debe procesar el Excel primero usando /pipeline/process-excel"
#         )
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error al descargar el archivo: {str(e)}"
#         )


# @router.get(
#     "/download-all",
#     summary="Descargar todos los CSVs",
#     description="""
#     Descarga un archivo ZIP con todos los CSVs procesados.
    
#     El ZIP contendrá un archivo CSV por cada complejidad que haya sido procesada exitosamente.
#     """,
#     responses={
#         200: {
#             "description": "ZIP descargado correctamente",
#             "content": {
#                 "application/zip": {}
#             }
#         },
#         404: {
#             "description": "No hay archivos procesados",
#         }
#     }
# )
# async def download_all_csvs():
#     """
#     Descarga un ZIP con todos los CSVs de complejidades procesadas.
#     """
#     complejidades = ['Alta', 'Media', 'Baja', 'Neonatología', 'Pediatría']
    
#     # Crear ZIP en memoria
#     zip_buffer = io.BytesIO()
    
#     with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
#         archivos_agregados = 0
        
#         for complejidad in complejidades:
#             filename = f"{complejidad}.csv"
            
#             try:
#                 df = storage_manager.load_csv(filename)
                
#                 # Agregar al ZIP
#                 csv_buffer = io.StringIO()
#                 df.to_csv(csv_buffer, index=False)
#                 zip_file.writestr(filename, csv_buffer.getvalue())
#                 archivos_agregados += 1
                
#             except FileNotFoundError:
#                 # Skip si no existe
#                 continue
#             except Exception as e:
#                 # Log error pero continuar
#                 print(f"Error al agregar {complejidad}: {e}")
#                 continue
    
#     if archivos_agregados == 0:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="No hay archivos CSV procesados disponibles. "
#                    "Debe procesar un Excel primero usando /pipeline/process-excel"
#         )
    
#     zip_buffer.seek(0)
    
#     return StreamingResponse(
#         zip_buffer,
#         media_type="application/zip",
#         headers={
#             "Content-Disposition": "attachment; filename=complejidades_procesadas.zip"
#         }
#     )


@router.get(
    "/status",
    summary="Estado del pipeline",
    description="""
    Obtiene el estado actual del pipeline y archivos procesados.
    
    Retorna información sobre qué complejidades han sido procesadas
    y están disponibles para descarga o predicción.
    """,
    responses={
        200: {
            "message": "Estado de los archivos del pipeline",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Estado de los archivos del pipeline",
                        "files": [
                          {
                            "name": "dataset",
                            "path": "data/dataset.csv",
                            "exists": False
                          },
                          {
                            "name": "predictions",
                            "path": "data/predictions.csv",
                            "exists": False
                          },
                          {
                            "name": "weekly",
                            "path": "data/weekly.csv",
                            "exists": False
                          },
                          {
                            "name": "models",
                            "path": "models",
                            "exists": False
                          }
                        ]
                    }
                }
            }
        },
        204: {
            "description": "El archivo excel de datos históricos no ha sido procesado",
        }
    }
)
async def pipeline_status():
    """
    Obtiene el estado del pipeline y archivos disponibles.
    """
    response = {
       "message": "Estado de los archivos del pipeline",
       "files": [
         {
           "name": "dataset",
           "path": "dataset.csv",
           "location": "s3",
           "exists": False
         },
         {
           "name": "predictions",
           "path": "predictions.csv",
           "location": "s3",
           "exists": False
         },
         {
           "name": "weekly",
           "path": "weekly.csv",
           "location": "s3",
           "exists": False
         },
         {
           "name": "models",
           "path": "models",
           "location": "local",
           "exists": False
         }
       ]
    }
    try:
      for file in response["files"]:
          if os.path.exists(file["path"]):
              file["exists"] = True
          else:
              file["exists"] = False
      return response
    except Exception as e:
      raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Error al obtener el estado del pipeline: {str(e)}"
      )

