from pathlib import Path
import pandas as pd
import numpy as np
import prophet
import joblib

def predict(complexity: str):
    """
    Realiza una predicción para una complejidad específica.
    
    Args:
        complexity: Nombre de la complejidad (Alta, Media, Baja, Neonatología, Pediatría)
    """
    # datos = {
    # "alta": {
    #     "demanda_pacientes": 50,
    #     "estancia (días)": 5.2,
    #     "tipo de paciente_No Qx": 0.6,
    #     "tipo de paciente Qx": 0.4,
    #     "tipo de ingreso_No Urgente": 0.7,
    #     "tipo de ingreso_Urgente": 0.3,
    #     "fecha ingreso completa": "2024-10-20"
    # },
    # "baja": {
    #     "demanda_pacientes": 30,
    #     "estancia (días)": 3.5,
    #     "tipo de paciente_No Qx": 0.8,
    #     "tipo de paciente Qx": 0.2,
    #     "tipo de ingreso_No Urgente": 0.85,
    #     "tipo de ingreso_Urgente": 0.15,
    #     "fecha ingreso completa": "2024-10-20"
    # },
    # "media": {
    #     "demanda_pacientes": 40,
    #     "estancia (días)": 4.5,
    #     "tipo de paciente_No Qx": 0.7,
    #     "tipo de paciente Qx": 0.3,
    #     "tipo de ingreso_No Urgente": 0.75,
    #     "tipo de ingreso_Urgente": 0.25,
    #     "fecha ingreso completa": "2024-10-20"
    # },
    # "neonatología": {
    #     "demanda_pacientes": 15,
    #     "estancia (días)": 8,
    #     "tipo de paciente_No Qx": 0.9,
    #     "tipo de paciente Qx": 0.1,
    #     "tipo de ingreso_No Urgente": 0.5,
    #     "tipo de ingreso_Urgente": 0.5,
    #     "fecha ingreso completa": "2024-10-20"
    # },
    # "pediatría": {
    #     "demanda_pacientes": 25,
    #     "estancia (días)": 4,
    #     "tipo de paciente_No Qx": 0.75,
    #     "tipo de paciente Qx": 0.25,
    #     "tipo de ingreso_No Urgente": 0.6,
    #     "tipo de ingreso_Urgente": 0.4,
    #     "fecha ingreso completa": "2024-10-20"
    # }
    # }

    # df_pred = preparar_datos_prediccion_global(datos)
    # print(df_pred.head())
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    ## Cargar datos desde CSV (CAMBIABLE)
    
    DATA_PATH = BASE_DIR / "data" / "datos_prediccion_semanal.csv"

    data_total = pd.read_csv(DATA_PATH)
    complexity = complexity.lower()
    df = data_total[data_total["complejidad"] == complexity]
    print(df.head())

    ## Cargar el modelo entrenado
    model_path = BASE_DIR / "models" / f"model_{complexity}.pkl"
    np.random.seed(42)
    model = joblib.load(model_path)
    print(f"Modelo cargado desde {model_path}")
    
    ## Realizar la predicción
    if complexity == "baja":
        print("Usando modelo Prophet")
        future = model.make_future_dataframe(periods=1, freq='W')

        forecast = model.predict(future)

        forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(12)
        print(forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(1))

    elif complexity == "media":
        print("🌲 Usando modelo RandomForest")
        print(df.head())
        print(df.columns)
        X_pred = df.drop(columns=["demanda_pacientes", "complejidad"])

        X_pred['año'] = X_pred['semana_año'].str.split('-').str[0].astype(int)
        X_pred['semana'] = X_pred['semana_año'].str.split('-').str[1].astype(int)

        X_pred['semana_continua'] = X_pred['año'] + X_pred['semana'] / 100

        X_pred = X_pred.drop(columns=['semana_año'])
        X_pred = X_pred.select_dtypes(exclude=['datetime64[ns]'])

        y_pred = model.predict(X_pred)
        result = {
            "modelo": "RandomForest",
            "prediccion": float(y_pred[-1]),
        }
        print(result)
    elif complexity == "alta":
        print("Usando modelo Random Forest")
        print(df.head())
        print(df.columns)
        X_pred = df.drop(columns=["demanda_pacientes", "complejidad"])

        X_pred['año'] = X_pred['semana_año'].str.split('-').str[0].astype(int)
        X_pred['semana'] = X_pred['semana_año'].str.split('-').str[1].astype(int)

        X_pred['semana_continua'] = X_pred['año'] + X_pred['semana'] / 100

        X_pred = X_pred.drop(columns=['semana_año'])
        X_pred = X_pred.select_dtypes(exclude=['datetime64[ns]'])

        y_pred = model.predict(X_pred)
        print(f"Predicción: {y_pred[-1]}")

    elif complexity == "neonatologia":
        future = model.make_future_dataframe(periods=1, freq='W')

        forecast = model.predict(future)

        forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(12)
        print(forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(1))
    elif complexity == "pediatria":
        future = model.make_future_dataframe(periods=1, freq='W')

        forecast = model.predict(future)

        forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(12)
        print(forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(1))
    
    return {"message": "Predicción realizada correctamente", "complexity": complexity}

