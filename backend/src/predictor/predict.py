from pathlib import Path
import pandas as pd
import numpy as np
import prophet
import joblib

def pre_process_X_pred(df: pd.DataFrame):
    X = df.drop(columns=["demanda_pacientes", "complejidad"])
    X['año'] = X['semana_año'].str.split('-').str[0].astype(int)
    X['semana'] = X['semana_año'].str.split('-').str[1].astype(int)
    X['semana_continua'] = X['año'] + X['semana'] / 100
    X = X.drop(columns=['semana_año'])
    X = X.select_dtypes(exclude=['datetime64[ns]'])
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
    
    DATA_PATH = BASE_DIR / "data" / "datos_prediccion_semanal.csv" # cambiar a prediccion.csv en prod

    data_total = pd.read_csv(DATA_PATH)
    complexity = complexity.lower()
    df = data_total[data_total["complejidad"] == complexity]
    print(df.head())
    try:
        model_path = BASE_DIR / "models" / f"model_{complexity}.pkl"
        np.random.seed(42)
        model = joblib.load(model_path)
    except Exception as e:
        print(f"modelo en formato no .pkl... probando json")
        model_path = BASE_DIR / "models" / f"model_{complexity}.json"
        model = joblib.load(model_path)

    ## Realizar la predicción
    if complexity == "baja":
        print("Usando modelo Prophet")
        result = predict_prophet_model(model, periods=1)
        print(result)
        return {"prediccion": result.to_dict(orient='records')}

    elif complexity == "media":
        print("🌲 Usando modelo RandomForest")
        print(df.head())
        print(df.columns)
        X_pred = pre_process_X_pred(df)
        result = predict_random_forest(model, X_pred)
        return result
    elif complexity == "alta":
        print("Usando modelo Random Forest")
        print(df.head())
        print(df.columns)
        X_pred = pre_process_X_pred(df)
        result = predict_random_forest(model, X_pred)
        return result
    elif complexity == "neonatologia":
        result = predict_prophet_model(model, periods=1)
        print(result)
        return {"prediccion": result.to_dict(orient='records')}

    elif complexity == "pediatria":
        result = predict_prophet_model(model, periods=1)
        print(result)
        return {"prediccion": result.to_dict(orient='records')}
    
    return {"message": "Predicción realizada correctamente", "complexity": complexity}

