import json
from pathlib import Path
import pandas as pd
import numpy as np
import prophet
import logging
from ..utils.storage import storage_manager
from ..utils.version import version_manager
from ..utils.complexities import ComplexityMapper

import os

logger = logging.getLogger(__name__)


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

def predict(complexity: str):
    """
    Realiza una predicción para una complejidad específica.
    
    Args:
        complexity: Nombre de la complejidad (Alta, Media, Baja, Neonatología, Pediatría)
    """

    data_total = storage_manager.load_csv('predictions.csv')

    df = data_total[data_total["complejidad"] == complexity]
    feature_names = version_manager.get_feature_names()

    complexity = ComplexityMapper.to_label(complexity)

    try:
        np.random.seed(42)
        model = version_manager.get_model(complexity)
        version = version_manager.get_active_version(complexity)
    except Exception as e:
        raise Exception(f"error {e}")


    if not ComplexityMapper.is_valid_label(complexity):
        raise Exception(f"Invalid complexity: {complexity}")

    # Get metrics: use version metadata if available, otherwise use base metrics
    if version:
        metrics_models = version_manager.get_version_metrics(complexity, version)
    else:
        logger.info(f"No version available for {complexity}, using base metrics")
        metrics_models = version_manager.get_base_metrics(complexity)
        if not metrics_models:
            logger.warning(f"No metrics found for {complexity}")
            metrics_models = {}
    
    result = predict_prophet_model(model, periods=1)
    prediccion = result.yhat.values[-1]
    lower = result.yhat_lower.values[-1]
    upper = result.yhat_upper.values[-1]    
    response = {"complexity": complexity, "prediction": prediccion, "lower": lower, "upper": upper, "MAE": metrics_models.get("MAE"), "RMSE": metrics_models.get("RMSE"), "R2": metrics_models.get("R2")}
    return response
