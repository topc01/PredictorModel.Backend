"""
Data cleaning pipeline for initial Excel processing.

This module handles the initial data cleaning from raw Excel files,
merging sheets, feature engineering, and creating per-complexity datasets.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, BinaryIO
import io


def get_season(month: int) -> str:
    """
    Obtiene la estación del año basada en el mes.
    
    Args:
        month: Número del mes (1-12)
        
    Returns:
        Nombre de la estación en español
    """
    if month in [12, 1, 2]:
        return "verano"
    elif month in [3, 4, 5]:
        return "otoño"
    elif month in [6, 7, 8]:
        return "invierno"
    else:
        return "primavera"


def limpiar_excel_inicial(archivo: BinaryIO) -> pd.DataFrame:
    """
    Limpia y procesa el archivo Excel inicial con datos hospitalarios.
    
    El archivo debe tener al menos 2 hojas:
    - Hoja 0: Datos principales de pacientes
    - Hoja 2: Datos de servicios/complejidad
    
    Args:
        archivo: Archivo Excel en formato binario (BytesIO o similar)
        
    Returns:
        DataFrame limpio con features creadas
        
    Raises:
        ValueError: Si el archivo no tiene el formato esperado
    """
    try:
        xls = pd.ExcelFile(archivo)
        
        if len(xls.sheet_names) < 3:
            raise ValueError(
                f"El archivo debe tener al menos 3 hojas. Encontradas: {len(xls.sheet_names)}"
            )
        
        # Leer las hojas necesarias
        df1 = pd.read_excel(archivo, sheet_name=xls.sheet_names[0])
        df3 = pd.read_excel(archivo, sheet_name=xls.sheet_names[2])
        
        # Merge de datos
        df = df1.merge(
            df3,
            left_on="Servicio Ingreso (Código)",
            right_on="UO trat.",
            how="left"
        )
        
        # Normalizar nombres de columnas
        df.columns = df.columns.str.strip()
        df.columns = df.columns.str.lower()
        df.columns = df.columns.str.replace(r"\s+", " ", regex=True).str.strip()
        
        # Columnas a eliminar
        cols_drop = [
            'id', 'edad en años', 'sexo (desc)', 'servicio egreso (código)',
            'peso grd', 'ir grd (código)', 'ir grd',
            'conjunto de servicios traslado', 'cx', 'uo trat.', 'desc. serv.'
        ]
        
        # Eliminar solo las columnas que existan
        cols_to_drop = [col for col in cols_drop if col in df.columns]
        df = df.drop(columns=cols_to_drop)
        
        # Crear features temporales
        df['fecha ingreso completa'] = pd.to_datetime(df['fecha ingreso completa'], errors='coerce')
        df['semana_ingreso'] = df['fecha ingreso completa'].dt.isocalendar().week
        df['año_ingreso'] = df['fecha ingreso completa'].dt.year
        df['mes_ingreso'] = df['fecha ingreso completa'].dt.month
        df['estacion'] = df['mes_ingreso'].apply(get_season)
        
        return df
        
    except Exception as e:
        raise ValueError(f"Error al procesar el archivo Excel: {str(e)}")


def preparar_datos_por_complejidad(df_original: pd.DataFrame, complejidad_valor: str) -> Optional[pd.DataFrame]:
    """
    Filtra y preprocesa los datos para una complejidad específica.
    
    Realiza:
    - Filtrado por complejidad
    - One-hot encoding de variables categóricas
    - Agrupación semanal
    - Creación de lags
    - Eliminación de columnas poco frecuentes
    
    Args:
        df_original: DataFrame con datos limpios
        complejidad_valor: Nombre de la complejidad ('Baja', 'Media', 'Alta', 'Neonatología', 'Pediatría')
        
    Returns:
        DataFrame procesado con features retrasadas, o None si no hay suficientes datos
    """
    # Filtrar por complejidad
    df_filtrado = df_original[df_original['complejidad'] == complejidad_valor].copy()
    
    # Verificar datos suficientes (al menos 55 semanas)
    if df_filtrado.shape[0] < 55:
        return None
    
    # Asegurar que la fecha esté en formato datetime
    df_filtrado['fecha_ingreso_completa'] = pd.to_datetime(
        df_filtrado['fecha ingreso completa'], 
        errors='coerce'
    )
    
    # One-hot encoding de variables categóricas
    categoricas = [
        'servicio ingreso (código)',
        'tipo de paciente',
        'tipo de ingreso',
        'estacion'
    ]
    df_encoded = pd.get_dummies(df_filtrado, columns=categoricas, drop_first=False)
    
    # Crear identificador semana-año
    df_encoded['semana_año'] = df_encoded['fecha_ingreso_completa'].dt.strftime('%Y-%U')
    
    # Configurar agregaciones
    agregaciones = {'estancia (días)': 'mean'}
    cols_ohe = [
        col for col in df_encoded.columns 
        if any(col.startswith(cat + '_') for cat in categoricas)
    ]
    for col in cols_ohe:
        agregaciones[col] = 'mean'
    
    # Agrupación semanal
    semanal = df_encoded.groupby('semana_año').agg(agregaciones).reset_index()
    
    # Contar pacientes por semana (demanda)
    conteos = df_encoded.groupby('semana_año').size().reset_index(name='demanda_pacientes')
    semanal = semanal.merge(conteos, on='semana_año', how='left')
    
    # Ordenar por semana
    semanal.sort_values(by='semana_año', inplace=True)
    
    # Filtrar semanas con demanda mínima (excepto Neonatología)
    if complejidad_valor != "Neonatología":
        semanal = semanal[semanal['demanda_pacientes'] >= 10].copy()
    
    semanal.reset_index(drop=True, inplace=True)
    
    # --- CREACIÓN DE LAGS ---
    
    # Lags de demanda
    for lag in [1, 2, 3, 4, 10, 52]:
        semanal[f'demanda_lag{lag}'] = semanal['demanda_pacientes'].shift(lag)
    
    # Retrasar todas las features (excepto semana_año y demanda)
    features_a_retrasar = [
        col for col in semanal.columns 
        if col not in ['semana_año', 'demanda_pacientes'] and 'demanda_lag' not in col
    ]
    
    for feature in features_a_retrasar:
        semanal[f'{feature}_lag1'] = semanal[feature].shift(1)
    
    # Eliminar columnas originales no retrasadas
    semanal.drop(columns=features_a_retrasar, inplace=True)
    
    # Eliminar filas con NaN de los shifts
    semanal.dropna(inplace=True)
    
    # Crear número de semana
    semanal['numero_semana'] = semanal['semana_año'].str.split('-').str[1].astype(int)
    
    # Eliminar columnas poco frecuentes/raras (servicios específicos)
    cols_a_eliminar = [
        'servicio ingreso (código)_UEMECLI4_lag1',
        'servicio ingreso (código)_UEMECLI5_lag1',
        'servicio ingreso (código)_UEMECLI6_lag1',
        'servicio ingreso (código)_UEMECLI7_lag1',
        'servicio ingreso (código)_UEMEQ2ED_lag1',
        'servicio ingreso (código)_UEMEQ4DE_lag1',
        'servicio ingreso (código)_UEMEQCLI_lag1',
        'servicio ingreso (código)_UEMEQX4A_lag1',
        'servicio ingreso (código)_UEMEQX4B_lag1',
        'servicio ingreso (código)_UEMEQX4C_lag1',
        'servicio ingreso (código)_UEMEQX5A_lag1',
        'servicio ingreso (código)_UEMEQX5B_lag1',
        'servicio ingreso (código)_UEMEQX5C_lag1',
        'servicio ingreso (código)_UEMULTI2_lag1',
        'servicio ingreso (código)_UEOCLI10_lag1',
        'servicio ingreso (código)_UEONCCLI_lag1',
        'servicio ingreso (código)_UEONCLI8_lag1',
        'servicio ingreso (código)_UEPENMAT_lag1',
        'servicio ingreso (código)_UEINAD_lag1',
        'servicio ingreso (código)_UEINAD4_lag1',
        'servicio ingreso (código)_UERECUP6_lag1',
        'servicio ingreso (código)_UEUNICOR_lag1'
    ]
    
    semanal = semanal.drop(columns=cols_a_eliminar, errors='ignore')
    
    return semanal


def procesar_excel_completo(archivo: BinaryIO) -> Dict[str, Optional[pd.DataFrame]]:
    """
    Procesa un archivo Excel completo y genera datasets por complejidad.
    
    Args:
        archivo: Archivo Excel en formato binario
        
    Returns:
        Diccionario con DataFrames por complejidad:
        {'Baja': df_baja, 'Media': df_media, ...}
    """
    # Limpiar datos iniciales
    df = limpiar_excel_inicial(archivo)
    
    # Procesar cada complejidad
    complejidades = ['Baja', 'Media', 'Alta', 'Neonatología', 'Pediatría']
    dfs_por_complejidad = {}
    
    for complejidad in complejidades:
        df_complejidad = preparar_datos_por_complejidad(df, complejidad)
        dfs_por_complejidad[complejidad] = df_complejidad
    
    return dfs_por_complejidad

