import pandas as pd
import numpy as np

from ..utils.storage import storage_manager

def preparar_datos_prediccion_global(datos_nuevos, filename="dataset.csv"):

    # 1️⃣ Cargar dataset histórico completo
    df_total = storage_manager.load_csv(filename)

    # Validar columnas
    if 'complejidad' not in df_total.columns:
        raise ValueError("El dataset no contiene una columna llamada 'complejidad'.")

    filas_prediccion = []

    # 2️⃣ Iterar sobre cada complejidad del input
    for complejidad_valor, datos in datos_nuevos.items():

        df_nueva = pd.DataFrame(datos)

        # Filtrar histórico de esa complejidad
        df_hist = df_total[df_total['complejidad'].str.lower() == complejidad_valor.lower()].copy()
        
        # --- Procesar fechas ---
        df_nueva['fecha_ingreso_completa'] = pd.to_datetime(df_nueva['Fecha ingreso'], errors='coerce')
        fecha_actual = df_nueva['fecha_ingreso_completa'].iloc[0]

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

        # 3️⃣ ***Primero actualizar la semana pasada en el dataset***
        mask = (
            (df_total['complejidad'].str.lower() == complejidad_valor.lower()) &
            (df_total['semana_año'] == semana_lag1)
        )
        demanda_real = df_nueva['Demanda pacientes'].iloc[0]

        if mask.any():
            df_total.loc[mask, 'demanda_pacientes'] = demanda_real
        else:
            print(f"⚠️ Semana {semana_lag1} no existe en dataset. No se crea.")

        # 4️⃣ Recalcular HISTÓRICO ya actualizado
        df_hist = df_total[df_total['complejidad'].str.lower() == complejidad_valor.lower()].copy()
        df_hist = df_hist.sort_values('semana_año')
        semanas_hist = df_hist['semana_año'].tolist()

        # 5️⃣ Construcción base de fila
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

        # 6️⃣ Rellenar lags con el dataset YA actualizado
        for lag in [1,2,3,4,10,52]:
            col = f'demanda_lag{lag}'
            if len(semanas_hist) >= lag:
                semana_ref = semanas_hist[-lag]
                fila[col] = df_hist[df_hist['semana_año'] == semana_ref]['demanda_pacientes'].mean()
            else:
                fila[col] = np.nan

        # 7️⃣ Agregar la fila de la nueva semana (sin demanda real)
        fila_dataset = fila.copy()
        df_total = pd.concat([df_total, pd.DataFrame([fila_dataset])], ignore_index=True)

        filas_prediccion.append(fila)

    # 8️⃣ Guardar dataset actualizado
    storage_manager.save_csv(df_total, filename)

    # 9️⃣ Generar archivo de predicción
    df_prediccion = pd.DataFrame(filas_prediccion)
    storage_manager.save_csv(df_prediccion, "predictions.csv")

    return df_prediccion
