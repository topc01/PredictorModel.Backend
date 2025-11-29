import json
from pathlib import Path
import pandas as pd
import numpy as np
import prophet
import joblib
from ..utils.storage import storage_manager
from ..retrain.retrain import get_prophet_models

import os

def without_tilde(string: str) -> str:
    return string.replace('í', 'i')

from datetime import datetime

def choose_best_model(models_info):
    models = models_info["models"]

    for m in models:
        m["trained_at_dt"] = datetime.strptime(m["trained_at"], "%Y-%m-%d %H:%M:%S")

    sorted_models = sorted(
        models,
        key=lambda m: (
            m["metrics"]["RMSE"],
            m["metrics"]["MAE"],
            -m["trained_at_dt"].timestamp()
        )
    )

    return sorted_models[0]

def pre_process_X_pred(df: pd.DataFrame, feature_names: list) -> pd.DataFrame:
    X = df.drop(columns=["demanda_pacientes", "complejidad"])
    X['año'] = X['semana_año'].str.split('-').str[0].astype(int)
    X['semana'] = X['semana_año'].str.split('-').str[1].astype(int)
    X['semana_continua'] = X['año'] + X['semana'] / 100
    X = X.drop(columns=['semana_año'])
    X = X.select_dtypes(exclude=['datetime64[ns]'])
    X = X[feature_names]
    return X

def predict_prophet_model(model, periods: int = 1):
    """
    Realiza una predicción utilizando un modelo Prophet.
    
    Args:
        model: Modelo Prophet entrenado.
        periods: Número de períodos futuros a predecir.
        
    Returns:
        DataFrame con las predicciones.
    """
    future = model.make_future_dataframe(periods=periods, freq='W')
    forecast = model.predict(future)
    return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)

def predict_random_forest(model, X_pred):
    """
    Realiza una predicción utilizando un modelo Random Forest.
    
    Args:
        model: Modelo Random Forest entrenado.
        X_pred: DataFrame con las características para la predicción.
        
    Returns:
        Diccionario con la predicción y el intervalo de confianza.
    """
    y_pred = model.predict(X_pred)

    tree_preds = np.array([tree.predict(X_pred) for tree in model.estimators_])  # matriz (n_trees, n_muestras)

    preds_ultimo = tree_preds[:, -1]

    mean_pred = np.mean(preds_ultimo)
    std_pred = np.std(preds_ultimo)

    lower = mean_pred - 1.96 * std_pred
    upper = mean_pred + 1.96 * std_pred

    return {
        "prediccion": float(y_pred[-1]),
        "intervalo_confianza": [lower, upper]
    }


def predict(complexity: str, version_to_load: str = None):
    """
    Realiza una predicción para una complejidad específica.
    
    Args:
        complexity: Nombre de la complejidad (Alta, Media, Baja, Neonatología, Pediatría)
        version_to_load: Versión del modelo a cargar (opcional)
    """

    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    data_total = storage_manager.load_csv('predictions.csv')

    df = data_total[data_total["complejidad"] == complexity]
    FEATURE_PATH = "models/feature_names.pkl"
    feature_names = joblib.load(FEATURE_PATH)

    try:
        np.random.seed(42)
        #Manejo de nombres con tildes
        if complexity == "Pediatría":
            complexity_to_load = "Pediatria"
        elif complexity == "Neonatología":
            complexity_to_load = "Neonatologia"
        else:
            complexity_to_load = complexity
        ###
        # Para seleccionar el modelo con mejor rendimiento
        if version_to_load == None:
            version = choose_best_model(get_prophet_models(complexity=complexity_to_load))["version"]
        else:
            version = version_to_load
        ######
        model = storage_manager.load_prophet_model(complexity_to_load, version)
    except Exception as e:
        raise Exception(f"error {e}")

    try:
        metrics_models = storage_manager.load_prophet_metrics(complexity_to_load, version)
        print(f"metricas del modelo: {metrics_models}")
    except Exception as e:
        raise Exception(f"error {e}")

    ## Realizar la predicción
    if complexity == "Baja":
        result = predict_prophet_model(model, periods=1)
        prediccion = result.yhat.values[-1]
        lower = result.yhat_lower.values[-1]
        upper = result.yhat_upper.values[-1]    
        response = {"complexity": complexity, "prediction": prediccion, "lower": lower, "upper": upper, "MAE": metrics_models.get("MAE"), "RMSE": metrics_models.get("RMSE"), "R2": metrics_models.get("R2")}
        return response
    elif complexity == "Maternidad":
        result = predict_prophet_model(model, periods=1)
        prediccion = result.yhat.values[-1]
        lower = result.yhat_lower.values[-1]
        upper = result.yhat_upper.values[-1]    
        response = {"complexity": complexity, "prediction": prediccion, "lower": lower, "upper": upper, "MAE": metrics_models.get("MAE"), "RMSE": metrics_models.get("RMSE"), "R2": metrics_models.get("R2")}
        return response
    elif complexity == "Media":
        result = predict_prophet_model(model, periods=1)
        prediccion = result.yhat.values[-1]
        lower = result.yhat_lower.values[-1]
        upper = result.yhat_upper.values[-1]    
        response = {"complexity": complexity, "prediction": prediccion, "lower": lower, "upper": upper, "MAE": metrics_models.get("MAE"), "RMSE": metrics_models.get("RMSE"), "R2": metrics_models.get("R2")}
        return response
    elif complexity == "Alta":
        result = predict_prophet_model(model, periods=1)
        prediccion = result.yhat.values[-1]
        lower = result.yhat_lower.values[-1]
        upper = result.yhat_upper.values[-1]    
        response = {"complexity": complexity, "prediction": prediccion, "lower": lower, "upper": upper, "MAE": metrics_models.get("MAE"), "RMSE": metrics_models.get("RMSE"), "R2": metrics_models.get("R2")}
        return response
    elif complexity == "Neonatología":
        result = predict_prophet_model(model, periods=1)
        prediccion = result.yhat.values[-1]
        lower = result.yhat_lower.values[-1]
        upper = result.yhat_upper.values[-1]    
        response = {"complexity": complexity, "prediction": prediccion, "lower": lower, "upper": upper, "MAE": metrics_models.get("MAE"), "RMSE": metrics_models.get("RMSE"), "R2": metrics_models.get("R2")}
        return response
    elif complexity == "Pediatría":
        result = predict_prophet_model(model, periods=1)
        prediccion = result.yhat.values[-1]
        lower = result.yhat_lower.values[-1]
        upper = result.yhat_upper.values[-1]    
        response = {"complexity": complexity, "prediction": prediccion, "lower": lower, "upper": upper, "MAE": metrics_models.get("MAE"), "RMSE": metrics_models.get("RMSE"), "R2": metrics_models.get("R2")}
        return response
    elif complexity == "Inte. Pediátrico" or complexity == "IntePediatrico":
        result = predict_prophet_model(model, periods=1)
        prediccion = result.yhat.values[-1]
        lower = result.yhat_lower.values[-1]
        upper = result.yhat_upper.values[-1]    
        response = {"complexity": complexity, "prediction": prediccion, "lower": lower, "upper": upper, "MAE": metrics_models.get("MAE"), "RMSE": metrics_models.get("RMSE"), "R2": metrics_models.get("R2")}
        return response
    raise Exception(f"Complejidad {complexity} no encontrada.")

