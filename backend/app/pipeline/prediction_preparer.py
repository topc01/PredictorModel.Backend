"""
Prediction data preparation module.

Prepares new weekly data for predictions by updating historical data
and creating properly lagged features.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional


def preparar_datos_prediccion_por_complejidad(
    df_historico: pd.DataFrame,
    df_nueva: pd.DataFrame,
    complejidad_valor: str
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Prepara la fila de predicción para una complejidad específica.
    
    Esta función:
    1. Toma los datos reales de la semana pasada
    2. Crea features con lag (retrasadas)
    3. Rellena lags históricos desde el DataFrame histórico
    4. Actualiza el DataFrame histórico con los nuevos datos
    5. Guarda el CSV actualizado
    
    Args:
        df_historico: DataFrame con datos históricos de la complejidad
        df_nueva: DataFrame con datos de la semana pasada. Debe contener:
            - demanda_pacientes: Cantidad real de pacientes
            - estancia (días): Promedio de estancia
            - tipo de paciente_No Qx: Proporción (0-1)
            - tipo de paciente_Qx: Proporción (0-1)
            - tipo de ingreso_No Urgente: Proporción (0-1)
            - tipo de ingreso_Urgente: Proporción (0-1)
            - fecha ingreso completa: Fecha de ingreso
        complejidad_valor: Nombre de la complejidad
        
    Returns:
        Tupla (semanal, df_historico_actualizado):
        - semanal: DataFrame con fila lista para predicción
        - df_historico_actualizado: DataFrame histórico con nuevos datos
        
    Raises:
        ValueError: Si los datos de entrada están vacíos o mal formateados
    """
    if df_nueva.empty:
        raise ValueError(f"No hay datos nuevos para la complejidad {complejidad_valor}")
    
    # --- 1️⃣ Procesar fechas ---
    df_nueva['fecha_ingreso_completa'] = pd.to_datetime(
        df_nueva['fecha ingreso completa'], 
        errors='coerce'
    )
    fecha_actual = df_nueva['fecha_ingreso_completa'].iloc[0]
    
    if pd.isna(fecha_actual):
        raise ValueError("Fecha de ingreso inválida")
    
    # Calcular semana actual y semana a predecir
    inicio_semana_actual = fecha_actual - pd.to_timedelta(fecha_actual.weekday(), unit='d')
    inicio_semana_predecir = inicio_semana_actual + pd.Timedelta(weeks=1)
    semana_a_predecir = f"{inicio_semana_predecir.isocalendar().year}-{str(inicio_semana_predecir.isocalendar().week).zfill(2)}"
    
    # Calcular estación de la semana actual
    mes = fecha_actual.month
    if mes in [12, 1, 2]:
        estacion = "verano"
    elif mes in [3, 4, 5]:
        estacion = "otoño"
    elif mes in [6, 7, 8]:
        estacion = "invierno"
    else:
        estacion = "primavera"
    
    # --- 2️⃣ Preparar fila semanal para predicción ---
    semanal = pd.DataFrame({
        'semana_año': [semana_a_predecir],
        'demanda_pacientes': [np.nan],  # valor a predecir
        'demanda_lag1': [np.nan],  # se rellenará después
        'demanda_lag2': [np.nan],
        'demanda_lag3': [np.nan],
        'demanda_lag4': [np.nan],
        'demanda_lag10': [np.nan],
        'demanda_lag52': [np.nan],
        'estancia (días)_lag1': df_nueva['estancia (días)'].iloc[0],
        'tipo de paciente_No Qx_lag1': df_nueva['tipo de paciente_No Qx'].iloc[0],
        'tipo de paciente_Qx_lag1': df_nueva['tipo de paciente_Qx'].iloc[0],
        'tipo de ingreso_No Urgente_lag1': df_nueva['tipo de ingreso_No Urgente'].iloc[0],
        'tipo de ingreso_Urgente_lag1': df_nueva['tipo de ingreso_Urgente'].iloc[0],
        'estacion_invierno_lag1': 1 if estacion == "invierno" else 0,
        'estacion_otoño_lag1': 1 if estacion == "otoño" else 0,
        'estacion_primavera_lag1': 1 if estacion == "primavera" else 0,
        'estacion_verano_lag1': 1 if estacion == "verano" else 0,
        'numero_semana': inicio_semana_predecir.isocalendar().week
    })
    
    # --- 3️⃣ Rellenar lags históricos ---
    df_hist = df_historico.sort_values('semana_año')
    semanas_hist = df_hist['semana_año'].tolist()
    
    for lag in [1, 2, 3, 4, 10, 52]:
        col = f'demanda_lag{lag}'
        if len(semanas_hist) >= lag:
            semana_ref = semanas_hist[-lag]
            valor_lag = df_hist[df_hist['semana_año'] == semana_ref]['demanda_pacientes'].mean()
            semanal[col] = valor_lag
        else:
            semanal[col] = np.nan
    
    # --- 4️⃣ Actualizar histórico con la semana pasada ---
    semana_lag1 = f"{inicio_semana_actual.isocalendar().year}-{str(inicio_semana_actual.isocalendar().week).zfill(2)}"
    demanda_real = df_nueva['demanda_pacientes'].iloc[0]
    
    if semana_lag1 in df_historico['semana_año'].values:
        # Actualizar fila existente
        df_historico.loc[df_historico['semana_año'] == semana_lag1, 'demanda_pacientes'] = demanda_real
    else:
        # Agregar nueva fila
        nueva_fila = {'semana_año': semana_lag1, 'demanda_pacientes': demanda_real}
        df_historico = pd.concat([df_historico, pd.DataFrame([nueva_fila])], ignore_index=True)
    
    return semanal, df_historico

