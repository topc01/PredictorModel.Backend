from prophet import Prophet
from pathlib import Path
import pandas as pd
import joblib
import os
import json
from datetime import datetime
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import numpy as np
from fastapi import HTTPException
from app.utils.version import version_manager, ComplexityMapper
from app.utils.storage import storage_manager
import logging

logger = logging.getLogger(__name__)

def save_prophet_model(model, metrics, complexity, df_prophet):

    if model is None:
        raise ValueError("El modelo Prophet no puede ser None.")

    if not isinstance(metrics, dict):
        raise ValueError("Las métricas deben ser un diccionario.")

    if df_prophet is None or df_prophet.empty:
        raise ValueError("df_prophet está vacío o no es válido.")

    if not isinstance(complexity, str) or not complexity.strip():
        raise ValueError("El campo 'complexity' debe ser un string no vacío.")

    metadata = {
        "complexity": complexity,
        "n_samples": df_prophet.shape[0],
        "params": {
            "yearly_seasonality": True,
            "weekly_seasonality": False,
            "daily_seasonality": False,
            "seasonality_mode": "additive"
        },
        "metrics": metrics
    }
    try:
        return version_manager.save_model(model, metadata)
    except Exception as e:
        raise IOError(f"Error saving model with version manager: {str(e)}")

def load_data(complexity: str):
    # BASE_DIR = Path(__file__).resolve().parent.parent.parent
    # DATA_PATH = BASE_DIR / "data" / "dataset (2).csv" ## cambiar por el real
    
    # df = pd.read_csv(DATA_PATH)

    df = storage_manager.load_csv("dataset.csv")
    #print("Data loaded for complexity:", df.head())
    # df = pd.read_csv(DATA_PATH)

    if df is None or df.empty:
        raise ValueError("El DataFrame cargado está vacío o es None.")

    # Convert label to real name if needed
    if ComplexityMapper.is_valid_label(complexity):
        complexity = ComplexityMapper.to_real_name(complexity)

    df = df[df["complejidad"] == complexity]

    if df.empty:
        raise ValueError(f"No hay datos disponibles para la complejidad: {complexity}")
    
    return df

def prepare_data_prophet(df: pd.DataFrame):
    """Function to prepare data for Prophet model.
    """
    if df is None or df.empty:
        raise ValueError("El DataFrame de entrada está vacío o es None.")
    
    df = df.copy()
    
    df['ds'] = pd.to_datetime(df['semana_año'] + '-1', format='%Y-%W-%w', errors='coerce')

    df = df.rename(columns={'demanda_pacientes': 'y'})

    df = df[['ds', 'y']].sort_values('ds')

    if df.empty:
        raise ValueError("Después de procesar y limpiar los datos, el DataFrame quedó vacío.")
    return df

def obtain_metrics_prophet(y_true, y_pred):
    """Function to obtain metrics for Prophet model.
    """
    from sklearn.metrics import mean_absolute_error, r2_score

    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)

    return {
        "MAE": float(mae),
        "R2": float(r2)
    }

def retrain_prophet_model(complexity: str):
    """"Function to retrain the Prophet model.
    """
    df = load_data(complexity)
    df_prophet = prepare_data_prophet(df)
    df_prophet = df_prophet.dropna()
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        seasonality_mode='additive'
    )

    model.fit(df_prophet)
        
    future = model.make_future_dataframe(periods=5, freq='W')

    forecast = model.predict(future)

    forecast = forecast[forecast['ds'].isin(df_prophet['ds'])]
    merged = df_prophet.merge(forecast[['ds', 'yhat']], on='ds')
    merged = merged.dropna()
    y_true = merged['y']
    y_pred = merged['yhat']

    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)


    metrics = {
        "MAE": float(mae),
        "RMSE": float(rmse),
        "R2": float(r2)
    }
    
    result = save_prophet_model(model, metrics, complexity, df_prophet)

    # print("saving model...")
    # version = f"prophet_v{1}_{datetime.now().strftime('%Y-%m-%d_%H-%M')}"
    # os.makedirs(f"models/{version}", exist_ok=True)
    # print(f"models/{version}")
    # joblib.dump(model, f"models/{version}/model.pkl")
    # json.dump(metrics, open(f"models/{version}/metrics.json", "w"), indent=4)
    # json.dump(model.params, open(f"models/{version}/params.json", "w"), indent=4)
    # Mostrar 

    ## Calculo de metricas


def retrain_model():
    """"Function to retrain the model.
    """
    print("Retraining models...")
    for complexity in ComplexityMapper.get_all_labels():
        retrain_prophet_model(complexity=complexity)
    print("Models retrained.")
    pass

def get_prophet_models(complexity: str):
    """
    Returns all saved Prophet model versions for a given complexity level.
    """
    BASE_MODELS_PATH = "models/prophet"

    # Convert label to real name if needed
    if ComplexityMapper.is_valid_label(complexity):
        complexity = ComplexityMapper.to_real_name(complexity)
    
    complexity_path = os.path.join(BASE_MODELS_PATH, complexity)
    try:
        if not os.path.exists(complexity_path):
            raise HTTPException(status_code=404, detail="No hay modelos guardados para esta complejidad.")

        versions = []

        for version_name in sorted(os.listdir(complexity_path)):
            version_path = os.path.join(complexity_path, version_name)

            metadata_path = os.path.join(version_path, "metadata.json")
            metrics_path = os.path.join(version_path, "metrics.json")

            metadata = {}
            if os.path.exists(metadata_path):
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)

            metrics = {}
            if os.path.exists(metrics_path):
                with open(metrics_path, "r") as f:
                    metrics = json.load(f)

            versions.append({
                "version": version_name,
                "complexity": complexity,
                "trained_at": metadata.get("trained_at"),
                "n_samples": metadata.get("n_samples"),
                "params": metadata.get("params", {}),
                "metrics": metrics
            })
    except Exception as e:
        print("Error loading models:", str(e))

    return {
        "complexity": complexity,
        "count": len(versions),
        "models": versions
    }