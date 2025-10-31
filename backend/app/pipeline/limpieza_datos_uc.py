"""
Data cleaning pipeline for initial Excel processing.

This module handles the initial data cleaning from raw Excel files,
merging sheets, feature engineering, and creating per-complexity datasets.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, BinaryIO

from ..utils.storage import storage_manager

filename = "dataset.csv"

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


def preparar_datos_por_complejidad(df_original, complejidad_valor):
    df_filtrado = df_original[df_original['complejidad'] == complejidad_valor].copy()
    if df_filtrado.shape[0] < 55:
        return None


    df_filtrado['fecha_ingreso_completa'] = pd.to_datetime(df_filtrado['fecha ingreso completa'], errors='coerce')
    df_filtrado['semana_año'] = df_filtrado['fecha_ingreso_completa'].dt.strftime('%Y-%U')
    conteo_total = df_filtrado.groupby('semana_año').size().reset_index(name='demanda_pacientes')
# Tipo de ingreso
    conteo_ingreso = df_filtrado.groupby(['semana_año', 'tipo de ingreso']).size().unstack(fill_value=0).reset_index()
    if 'Urgente' not in conteo_ingreso.columns:
        conteo_ingreso['Urgente'] = 0
    if 'No Urgente' not in conteo_ingreso.columns:
        conteo_ingreso['No Urgente'] = 0
    conteo_ingreso.rename(columns={
        'Urgente': 'tipo de ingreso_Urgente',
        'No Urgente': 'tipo de ingreso_No Urgente'
    }, inplace=True)

    # Tipo de paciente
    conteo_paciente = df_filtrado.groupby(['semana_año', 'tipo de paciente']).size().unstack(fill_value=0).reset_index()
    if 'Qx' not in conteo_paciente.columns:
        conteo_paciente['Qx'] = 0
    if 'No Qx' not in conteo_paciente.columns:
        conteo_paciente['No Qx'] = 0
    conteo_paciente.rename(columns={
        'Qx': 'tipo de paciente_Qx',
        'No Qx': 'tipo de paciente_No Qx'
    }, inplace=True)


    categoricas = ['servicio ingreso (código)', 'estacion']
    df_encoded = pd.get_dummies(df_filtrado, columns=categoricas, drop_first=False)

    # df_encoded['semana_año'] = df_encoded['fecha_ingreso_completa'].dt.strftime('%Y-%U')

    
    # --- Agregaciones semanales ---
    agregaciones = {'estancia (días)': 'mean'}
    cols_ohe = [col for col in df_encoded.columns if any(col.startswith(cat + '_') for cat in categoricas)]
    for col in cols_ohe:
        agregaciones[col] = 'mean'

    semanal = df_encoded.groupby('semana_año').agg(agregaciones).reset_index()
    semanal = (
        semanal.merge(conteo_total, on='semana_año', how='left')
               .merge(conteo_ingreso, on='semana_año', how='left')
               .merge(conteo_paciente, on='semana_año', how='left')
    )

    # --- Limpieza por demanda mínima ---
    if complejidad_valor != "Neonatología":
        semanal = semanal[semanal['demanda_pacientes'] >= 10].copy()

    semanal.sort_values(by='semana_año', inplace=True)
    semanal.reset_index(drop=True, inplace=True)

    # --- Creación de lags ---
    for lag in [1, 2, 3, 4, 10, 52]:
        semanal[f'demanda_lag{lag}'] = semanal['demanda_pacientes'].shift(lag)

    features_a_retrasar = [col for col in semanal.columns if col not in ['semana_año', 'demanda_pacientes'] and 'demanda_lag' not in col]
    for feature in features_a_retrasar:
        semanal[f'{feature}_lag1'] = semanal[feature].shift(1)
    semanal.drop(columns=features_a_retrasar, inplace=True)

    semanal.dropna(inplace=True)
    semanal['numero_semana'] = semanal['semana_año'].str.split('-').str[1].astype(int)

    semanal['complejidad'] = complejidad_valor

    # Elimina columnas no deseadas (opcional)
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
        'servicio ingreso (código)_UEUNICOR_lag1',
        'servicio ingreso (código)_UEINT8_lag1',
       'servicio ingreso (código)_UEINTCLI_lag1',
       'servicio ingreso (código)_UEINTM5B_lag1',
       'servicio ingreso (código)_UEINTM5C_lag1',
       'servicio ingreso (código)_UETRAME2_lag1',
       'servicio ingreso (código)_UETRAMEN_lag1',
       'servicio ingreso (código)_UENEONAT_lag1',
       'servicio ingreso (código)_UEINMPED_lag1',
       'servicio ingreso (código)_UEINSPED_lag1',
       'servicio ingreso (código)_UEONCPED_lag1',
       'servicio ingreso (código)_UEPEDCLI_lag1',
       'servicio ingreso (código)_UEPEDIAT_lag1'
    ]
    semanal.drop(columns=cols_a_eliminar, errors='ignore', inplace=True)

    return semanal

def cargar_df_por_complejidad(ruta_csv, complejidad_valor):
    df = pd.read_csv(ruta_csv)
    if 'complejidad' not in df.columns:
        raise ValueError("El dataset no contiene una columna llamada 'complejidad'.")

    # Filtrar
    df_filtrado = df[df['complejidad'].str.lower() == complejidad_valor.lower()].copy()
    df_filtrado.drop(columns=['complejidad'], inplace=True)
    # if df_filtrado.empty:
    #     print(f"⚠️ No se encontraron filas para la complejidad '{complejidad_valor}'.")
    # else:
    #     print(f"✅ Dataset cargado: {len(df_filtrado)} filas para '{complejidad_valor}'")

    return df_filtrado



def procesar_excel_completo(archivo: BinaryIO) -> None:
    """
    Procesa un archivo Excel completo y genera datasets por complejidad.
    
    Args:
        archivo: Archivo Excel en formato binario
        
    Returns:
        None
    """
    # Limpiar datos iniciales
    df = limpiar_excel_inicial(archivo)
    
    # Procesar cada complejidad
    complejidades = ['Baja', 'Media', 'Alta', 'Neonatología', 'Pediatría']
    dfs_todos = []

    for c in complejidades:
        df_c = preparar_datos_por_complejidad(df, c)
        if df_c is not None:
            dfs_todos.append(df_c)
    
    df_final = pd.concat(dfs_todos, ignore_index=True).sort_values(['semana_año', 'complejidad'])
    df_final.to_csv("data/dataset.csv", index=False)
