import pandas as pd
import numpy as np

from ..utils.storage import storage_manager

def preparar_datos_prediccion_global(datos_nuevos, filename="dataset.csv"):

    # 1️⃣ Cargar dataset histórico completo
    df_total = storage_manager.load_csv(filename)
    # df_total = pd.read_csv(f"data/{filename}")

    # Validar columnas
    if 'complejidad' not in df_total.columns:
        raise ValueError("El dataset no contiene una columna llamada 'complejidad'.")

    filas_prediccion = []
    # 2️⃣ Iterar sobre cada complejidad del input
    for complejidad_valor, datos in datos_nuevos.items():

        # Convertir a DataFrame
        df_nueva = pd.DataFrame(datos)

        # Filtrar histórico de esa complejidad
        df_hist = df_total[df_total['complejidad'].str.lower() == complejidad_valor.lower()].copy()
        
        # --- Procesar fechas ---
        df_nueva['fecha_ingreso_completa'] = pd.to_datetime(df_nueva['Fecha ingreso'], errors='coerce')
        fecha_actual = df_nueva['fecha_ingreso_completa'].iloc[0]
        # Semana actual y a predecir
        inicio_semana_actual = fecha_actual - pd.to_timedelta(fecha_actual.weekday(), unit='d')
        inicio_semana_predecir = inicio_semana_actual + pd.Timedelta(weeks=1)
        semana_a_predecir = f"{inicio_semana_predecir.isocalendar().year}-{str(inicio_semana_predecir.isocalendar().week).zfill(2)}"
        semana_lag1 = f"{inicio_semana_actual.isocalendar().year}-{str(inicio_semana_actual.isocalendar().week).zfill(2)}"

        # --- Calcular estación ---
        mes = fecha_actual.month
        if mes in [12, 1, 2]:
            estacion = "verano"
        elif mes in [3,4,5]:
            estacion = "otoño"
        elif mes in [6,7,8]:
            estacion = "invierno"
        else:
            estacion = "primavera"

        # --- Preparar fila semanal ---
        fila = {
            'semana_año': semana_a_predecir,
            'demanda_pacientes': np.nan,
            'demanda_lag1': np.nan,
            'demanda_lag2': np.nan,
            'demanda_lag3': np.nan,
            'demanda_lag4': np.nan,
            'demanda_lag10': np.nan,
            'demanda_lag52': np.nan,
            'estancia (días)_lag1': df_nueva['Estancia (días promedio)'].iloc[0],
            'tipo de paciente_No Qx_lag1': df_nueva['Pacientes no Qx'].iloc[0],
            'tipo de paciente_Qx_lag1': df_nueva['Pacientes Qx'].iloc[0],
            'tipo de ingreso_No Urgente_lag1': df_nueva['Ingresos no urgentes'].iloc[0],
            'tipo de ingreso_Urgente_lag1': df_nueva['Ingresos urgentes'].iloc[0],
            'estacion_invierno_lag1': 1 if estacion=="invierno" else 0,
            'estacion_otoño_lag1': 1 if estacion=="otoño" else 0,
            'estacion_primavera_lag1': 1 if estacion=="primavera" else 0,
            'estacion_verano_lag1': 1 if estacion=="verano" else 0,
            'numero_semana': inicio_semana_predecir.isocalendar().week,
            'complejidad': complejidad_valor
        }

        # --- Rellenar lags históricos ---
        df_hist = df_hist.sort_values('semana_año')
        semanas_hist = df_hist['semana_año'].tolist()
        for lag in [1,2,3,4,10,52]:
            col = f'demanda_lag{lag}'
            if len(semanas_hist) >= lag:
                semana_ref = semanas_hist[-lag]
                fila[col] = df_hist[df_hist['semana_año']==semana_ref]['demanda_pacientes'].mean()
            else:
                fila[col] = np.nan

        # --- Actualizar dataset global directamente ---
        mask = (df_total['complejidad'].str.lower() == complejidad_valor.lower()) & (df_total['semana_año'] == semana_lag1)
        demanda_real = df_nueva['Demanda pacientes'].iloc[0]

        if mask.any():
            df_total.loc[mask, 'demanda_pacientes'] = demanda_real
        else:
            nueva_fila = {
                'semana_año': semana_lag1,
                'demanda_pacientes': demanda_real,
                'complejidad': complejidad_valor
            }
            df_total = pd.concat([df_total, pd.DataFrame([nueva_fila])], ignore_index=True)

        filas_prediccion.append(fila)

    # --- Guardar dataset actualizado ---
    storage_manager.save_csv(df_total, filename)
    # df_total.to_csv(f"data/{filename}", index=False)

    # --- Generar CSV con los nuevos datos de predicción ---
    df_prediccion = pd.DataFrame(filas_prediccion)
    storage_manager.save_csv(df_prediccion, "predictions.csv")
    # df_prediccion.to_csv(f"data/predictions.csv", index=False)
    # print(f"✅ Dataset actualizado: {ruta_dataset}")
    # print(f"✅ Archivo de predicciones generado: datos_prediccion_semanal.csv")

    return df_prediccion



##### EJEMPLO DE USO
# datos = {
#   "alta": {
#     "demanda_pacientes": 50,
#     "estancia (días)": 5.2,
#     "tipo de paciente_No Qx": 0.6,
#     "tipo de paciente Qx": 0.4,
#     "tipo de ingreso_No Urgente": 0.7,
#     "tipo de ingreso_Urgente": 0.3,
#     "fecha ingreso completa": "2024-10-20"
#   },
#   "baja": {
#     "demanda_pacientes": 30,
#     "estancia (días)": 3.5,
#     "tipo de paciente_No Qx": 0.8,
#     "tipo de paciente Qx": 0.2,
#     "tipo de ingreso_No Urgente": 0.85,
#     "tipo de ingreso_Urgente": 0.15,
#     "fecha ingreso completa": "2024-10-20"
#   },
#   "media": {
#     "demanda_pacientes": 40,
#     "estancia (días)": 4.5,
#     "tipo de paciente_No Qx": 0.7,
#     "tipo de paciente Qx": 0.3,
#     "tipo de ingreso_No Urgente": 0.75,
#     "tipo de ingreso_Urgente": 0.25,
#     "fecha ingreso completa": "2024-10-20"
#   },
#   "neonatología": {
#     "demanda_pacientes": 15,
#     "estancia (días)": 8,
#     "tipo de paciente_No Qx": 0.9,
#     "tipo de paciente Qx": 0.1,
#     "tipo de ingreso_No Urgente": 0.5,
#     "tipo de ingreso_Urgente": 0.5,
#     "fecha ingreso completa": "2024-10-20"
#   },
#   "pediatría": {
#     "demanda_pacientes": 25,
#     "estancia (días)": 4,
#     "tipo de paciente_No Qx": 0.75,
#     "tipo de paciente Qx": 0.25,
#     "tipo de ingreso_No Urgente": 0.6,
#     "tipo de ingreso_Urgente": 0.4,
#     "fecha ingreso completa": "2024-10-20"
#   }
# }

# df_pred = preparar_datos_prediccion_global(datos)

# ACTUALIZA EL dataset.csv original
