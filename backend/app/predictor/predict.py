import json
from pathlib import Path
import pandas as pd
import numpy as np
import prophet
import joblib

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

def predict(complexity: str):
    """
    Realiza una predicción para una complejidad específica.
    
    Args:
        complexity: Nombre de la complejidad (Alta, Media, Baja, Neonatología, Pediatría)
    """

    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    ## Cargar datos desde CSV (CAMBIABLE)
    
    DATA_PATH = BASE_DIR / "data" / "predictions.csv"

    data_total = pd.read_csv(DATA_PATH)
    complexity = complexity.lower()
    df = data_total[data_total["complejidad"] == complexity]
    print(df.head())

    feature_names = joblib.load("models/feature_names.pkl")

    try:
        model_path = BASE_DIR / "models" / f"model_{complexity}.pkl"
        np.random.seed(42)
        model = joblib.load(model_path)
        print(f"modelo cargado en pkl")
    except Exception as e:
        print(f"error {e}")

    try:
        result_path = BASE_DIR / "models" / f"results_{complexity}.json"
        with open(result_path, "r", encoding="utf-8") as f:
            metrics_models = json.load(f)
        print("Resultados cargados desde JSON:")
        print(metrics_models)
    except Exception as e:
        print(f"No se pudo cargar resultados desde JSON: {e}")

    ## Realizar la predicción
    if complexity == "Baja":
        result = predict_prophet_model(model, periods=1)
        prediccion = result.yhat.values[-1]
        lower = result.yhat_lower.values[-1]
        upper = result.yhat_upper.values[-1]    
        response = {"complexity": complexity, "prediction": prediccion, "lower": lower, "upper": upper, "MAE": metrics_models.get("MAE"), "RMSE": metrics_models.get("RMSE"), "R2": metrics_models.get("R2")}
        return response
    elif complexity == "Media":
        X_pred = pre_process_X_pred(df, feature_names)
        result = predict_random_forest(model, X_pred)
        prediccion = result["prediccion"]
        lower = result["intervalo_confianza"][0]
        upper = result["intervalo_confianza"][1]
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

