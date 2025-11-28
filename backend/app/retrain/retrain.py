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
from app.utils.version import version_manager
from app.utils.storage import storage_manager

def save_prophet_model(model, metrics, complexity, df_prophet):
    version = f"v_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    base_path = f"models/prophet/{complexity}/{version}"
    os.makedirs(base_path, exist_ok=True)

    joblib.dump(model, f"{base_path}/model.pkl")

    with open(f"{base_path}/metrics.json", "w") as f:
        json.dump(metrics, f, indent=4)

    metadata = {
        "version": version,
        "complexity": complexity,
        "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "n_samples": df_prophet.shape[0],
        "params": {
            "yearly_seasonality": True,
            "weekly_seasonality": False,
            "daily_seasonality": False,
            "seasonality_mode": "additive"
        }
    }

    version_manager.save_model(model, metadata)
    with open(f"{base_path}/metadata.json", "w") as f:
        json.dump(metadata, f, indent=4)

    return {
        "version": version,
        "path": base_path,
        "metrics": metrics
    }

def load_data(complexity: str):
    # BASE_DIR = Path(__file__).resolve().parent.parent.parent
    # DATA_PATH = BASE_DIR / "data" / "dataset_prueba.csv" ## cambiar por el real
    df = storage_manager.load_csv("dataset.csv")
    # df = pd.read_csv(DATA_PATH)

    if complexity == "Pediatria":
        complexity = "Pediatría"
    elif complexity == "Neonatologia":
        complexity = "Neonatología"
    df = df[df["complejidad"] == complexity]
    print("Data loaded for retraining.")
    return df

def prepare_data_prophet(df: pd.DataFrame):
    """Function to prepare data for Prophet model.
    """
    
    df['ds'] = pd.to_datetime(df['semana_año'] + '-1', format='%Y-%W-%w', errors='coerce')

    df = df.rename(columns={'demanda_pacientes': 'y'})

    df = df[['ds', 'y']].sort_values('ds')
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
    print(df_prophet.head())
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        seasonality_mode='additive'
    )

    model.fit(df_prophet)
    
        
    future = model.make_future_dataframe(periods=1, freq='W')

    forecast = model.predict(future)

    forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(12)
    merged = df_prophet.merge(forecast[['ds', 'yhat']], on='ds')

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
    print("metrics:", metrics)
    
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
    print("Retraining model...")
    for e in ["Baja", "Media", "Alta", "Neonatologia", "Pediatria"]:
    # for e in ["Baja"]:
        retrain_prophet_model(complexity=e)
    pass

def get_prophet_models(complexity: str):
    print(f"Getting Prophet models for complexity: {complexity}")
    """
    Returns all saved Prophet model versions for a given complexity level.
    """
    BASE_MODELS_PATH = "models/prophet"

    complexity_path = os.path.join(BASE_MODELS_PATH, complexity)
    try:
        complexity = complexity.replace("Neonatologia", "Neonatología").replace("Pediatria", "Pediatría")
    except:
        pass
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