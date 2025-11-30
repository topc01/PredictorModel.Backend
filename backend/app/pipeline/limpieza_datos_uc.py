"""
Data cleaning pipeline for initial Excel processing.

This module handles the initial data cleaning from raw Excel files,
merging sheets, feature engineering, and creating per-complexity datasets.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, BinaryIO

from ..utils.storage import storage_manager
from ..utils.complexities import ComplexityMapper

filename = "dataset.csv"

def rellenar_complejidades_faltantes(df, lista_complejidades):
    """
    Asegura que cada semana tenga todas las complejidades.
    Cuando falta una, crea una fila con TODOS los valores = 0,
    excepto 'semana_año' y 'complejidad'.
    """
    semanas = df['semana_año'].unique()
    columnas = df.columns.tolist()

    filas_nuevas = []

    for semana in semanas:
        existentes = df[df['semana_año'] == semana]['complejidad'].str.lower().tolist()

        for comp in lista_complejidades:
            if comp.lower() not in existentes:

                # Crear fila nueva con TODO = 0
                fila = {col: 0 for col in columnas}

                # Sobrescribir las columnas clave
                fila['semana_año'] = semana
                fila['complejidad'] = comp

                filas_nuevas.append(fila)

    if filas_nuevas:
        df = pd.concat([df, pd.DataFrame(filas_nuevas)], ignore_index=True)

    return df


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
    except Exception as e:
        raise FileNotFoundError(f"[ERROR] No se pudo leer el archivo '{archivo}'. Detalle: {e}")

    try:
        df1 = pd.read_excel(archivo, sheet_name=xls.sheet_names[0])
        df3 = pd.read_excel(archivo, sheet_name=xls.sheet_names[2])
        print("[INFO] Hojas cargadas correctamente.")
    except Exception as e:
        raise ValueError(f"[ERROR] No se pudieron leer las hojas del Excel. Detalle: {e}")

    print("[INFO] Realizando merge...")

    if "Servicio Ingreso (Código)" not in df1.columns:
        raise KeyError("[ERROR] df1 no contiene la columna 'Servicio Ingreso (Código)'.")

    if "UO trat." not in df3.columns:
        raise KeyError("[ERROR] df3 no contiene la columna 'UO trat.'.")

    df = df1.merge(
        df3,
        left_on="Servicio Ingreso (Código)",
        right_on="UO trat.",
        how="left"
    )

    print("[INFO] Merge finalizado. Forma del df:", df.shape)

    # Normalización de columnas
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

    # Validación columna desc. serv.
    if "desc. serv." not in df.columns:
        raise KeyError("[ERROR] No existe la columna 'desc. serv.' en el DataFrame después del merge.")

    print("[INFO] Asignando complejidad según desc. serv....")

    # === MAPEO DE COMPLEJIDAD ===
    df['complejidad'] = np.where(
        df['desc. serv.'].isin([
            'Intermedio Pediátrico',
            'Intensivo Pediátrico'
        ]),
        'Inte. Pediátrico',
        df.get('complejidad', np.nan)
    )

    df['complejidad'] = np.where(
        df['desc. serv.'].isin([
            'Pediatría',
            'Oncología Pediátrica'
        ]),
        'Pediatría',
        df['complejidad']
    )

    df['complejidad'] = np.where(
        (df['complejidad'] == 'Baja') & (df['desc. serv.'] == 'Maternidad'),
        'Maternidad',
        df['complejidad']
    )

    if df['complejidad'].isna().sum() > 0:
        print(f"[WARNING] Hay {df['complejidad'].isna().sum()} filas donde complejidad quedó como NaN.")

    # === DROP ===
    cols_drop = [
        'id', 'edad en años', 'sexo (desc)', 'servicio egreso (código)',
        'peso grd', 'ir grd (código)', 'ir grd', 'conjunto de servicios traslado',
        'cx', 'uo trat.', 'desc. serv.'
    ]
    print("[INFO] Eliminando columnas no necesarias...")

    df = df.drop(columns=cols_drop, errors='ignore')

    # === FECHAS ===
    print("[INFO] Procesando fechas...")
    if "fecha ingreso completa" not in df.columns:
        raise KeyError("[ERROR] No existe la columna 'fecha ingreso completa' en el DataFrame.")

    df['fecha_ingreso_completa'] = pd.to_datetime(df['fecha ingreso completa'], errors='coerce')

    if df['fecha_ingreso_completa'].isna().sum() > 0:
        print("[WARNING] Hay fechas inválidas convertidas a NaT.")

    df['semana_ingreso'] = df['fecha_ingreso_completa'].dt.isocalendar().week
    df['año_ingreso'] = df['fecha_ingreso_completa'].dt.year
    df['mes_ingreso'] = df['fecha_ingreso_completa'].dt.month

    print("[INFO] Fechas procesadas correctamente.")

    print("[INFO] Calculando estación...")
    df['estacion'] = df['mes_ingreso'].apply(get_season)

    return df


def preparar_datos_por_complejidad(df_original, complejidad_valor):
    print(f"\n=== Procesando COMPLEJIDAD: {complejidad_valor} ===")

    try:
        df_filtrado = df_original[df_original['complejidad'] == complejidad_valor].copy()
    except Exception as e:
        raise ValueError(f"[ERROR] No se pudo filtrar por complejidad '{complejidad_valor}'. Detalle: {e}")

    if df_filtrado.empty:
        raise ValueError(f"[ERROR] No existen filas con complejidad '{complejidad_valor}'.")

    print(f"[INFO] Filtrado: {df_filtrado.shape[0]} filas")

    if df_filtrado.shape[0] < 55:
        print(f"[WARNING] Complejidad '{complejidad_valor}' tiene menos de 55 filas. Se omite.")
        return None

    # TODO LO DEMÁS DEL PIPELINE IGUAL — solo agrego verbose
    print("[INFO] Calculando semana del año...")
    df_filtrado['fecha_ingreso_completa'] = pd.to_datetime(df_filtrado['fecha ingreso completa'], errors='coerce')
    df_filtrado['semana_año'] = df_filtrado['fecha_ingreso_completa'].dt.strftime('%Y-%U')

    print("[INFO] Calculando conteos...")
    conteo_total = df_filtrado.groupby('semana_año').size().reset_index(name='demanda_pacientes')

    # (resto intacto pero con prints)
    print("[INFO] Generando conteos por tipo de ingreso...")
    conteo_ingreso = df_filtrado.groupby(['semana_año', 'tipo de ingreso']).size().unstack(fill_value=0).reset_index()

    print("[INFO] Generando conteos por tipo de paciente...")
    conteo_paciente = df_filtrado.groupby(['semana_año', 'tipo de paciente']).size().unstack(fill_value=0).reset_index()

    print("[INFO] OneHotEncoding columnas categóricas...")
    categoricas = ['servicio ingreso (código)', 'estacion']
    df_encoded = pd.get_dummies(df_filtrado, columns=categoricas, drop_first=False)

    print("[INFO] Agregando datos por semana...")
    agregaciones = {'estancia (días)': 'mean'}

    cols_ohe = [col for col in df_encoded.columns if any(col.startswith(cat + '_') for cat in categoricas)]
    for col in cols_ohe:
        agregaciones[col] = 'mean'

    semanal = df_encoded.groupby('semana_año').agg(agregaciones).reset_index()

    print("[INFO] Merge de agregados...")
    semanal = (
        semanal.merge(conteo_total, on='semana_año', how='left')
               .merge(conteo_ingreso, on='semana_año', how='left')
               .merge(conteo_paciente, on='semana_año', how='left')
    )

    print("[INFO] Eliminando semanas con baja demanda...")
    if complejidad_valor != "Neonatología":
        semanal = semanal[semanal['demanda_pacientes'] >= 10].copy()

    print("[INFO] Creando lags...")
    for lag in [1, 2, 3, 4, 10, 52]:
        semanal[f'demanda_lag{lag}'] = semanal['demanda_pacientes'].shift(lag)

    print("[INFO] Retasando features...")
    features_a_retrasar = [col for col in semanal.columns if col not in ['semana_año', 'demanda_pacientes'] and 'demanda_lag' not in col]

    for feature in features_a_retrasar:
        semanal[f'{feature}_lag1'] = semanal[feature].shift(1)

    semanal.drop(columns=features_a_retrasar, inplace=True)

    print("[INFO] Eliminando NaN...")
    semanal.dropna(inplace=True)

    print("[INFO] Extrayendo número de semana...")
    semanal['numero_semana'] = semanal['semana_año'].str.split('-').str[1].astype(int)

    print("[INFO] Agregando columna de complejidad...")
    semanal['complejidad'] = complejidad_valor

    print("[INFO] Eliminando columnas no deseadas...")
    cols_a_eliminar = [
        # (lista intacta)
        'servicio ingreso (código)_UEMECLI4_lag1',
        'servicio ingreso (código)_UEMECLI5_lag1',
        'servicio ingreso (código)_UEMECLI6_lag1',
        ...
    ]
    semanal.drop(columns=cols_a_eliminar, errors='ignore', inplace=True)

    print(f"[SUCCESS] COMPLEJIDAD '{complejidad_valor}' procesada. Filas finales:", semanal.shape[0])
    return semanal

def cargar_df_por_complejidad(ruta_csv, complejidad_valor):
    print(f"[INFO] Cargando CSV: {ruta_csv}")

    try:
        df = pd.read_csv(ruta_csv)
    except Exception as e:
        raise FileNotFoundError(f"[ERROR] No se pudo cargar el CSV '{ruta_csv}'. Detalle: {e}")

    if 'complejidad' not in df.columns:
        raise KeyError("[ERROR] El dataset no contiene una columna llamada 'complejidad'.")

    print(f"[INFO] Filtrando por complejidad: {complejidad_valor}")
    df_filtrado = df[df['complejidad'].str.lower() == complejidad_valor.lower()].copy()

    if df_filtrado.empty:
        raise ValueError(f"[ERROR] No existen filas con complejidad '{complejidad_valor}' en el archivo.")

    df_filtrado.drop(columns=['complejidad'], inplace=True)
    print("[SUCCESS] Datos cargados correctamente.")

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
    
    # Procesar cada complejidad (using centralized mapper)
    complejidades = ComplexityMapper.get_all_real_names()

    dfs_todos = []

    for c in complejidades:
        try:
            df_c = preparar_datos_por_complejidad(df, c)
            if df_c is not None:
                dfs_todos.append(df_c)
        except Exception as e:
            print(f"[ERROR] Falló el procesamiento de {c}: {e}")
    
    df_final = pd.concat(dfs_todos, ignore_index=True).sort_values(['semana_año', 'complejidad'])
    # 🔥 FIX: agregar complejidades faltantes en cada semana
    df_final = rellenar_complejidades_faltantes(df_final, lista_complejidades=ComplexityMapper.get_all_real_names())

    # Reordenar y guardar
    df_final = df_final.sort_values(['semana_año', 'complejidad']).reset_index(drop=True)
    storage_manager.save_csv(df_final, "dataset.csv")
    # df_final.to_csv("data/dataset.csv", index=False)
