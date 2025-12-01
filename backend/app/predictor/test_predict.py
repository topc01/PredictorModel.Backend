import pytest
from datetime import datetime
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
# Importa tus funciones correctamente:
from app.predictor.predict import without_tilde, choose_best_model

from app.predictor.predict import (
    pre_process_X_pred,
    predict_prophet_model
)
# ============================================================
# TEST without_tilde
# ============================================================

def test_without_tilde_basic():
    assert without_tilde("índice") == "indice"
    assert without_tilde("país") == "país".replace("í", "i")
    assert without_tilde("sin tilde") == "sin tilde"
    assert without_tilde("aquí y allí") == "aqui y alli"


def test_without_tilde_no_change():
    assert without_tilde("normal") == "normal"
    assert without_tilde("") == ""


# ============================================================
# TEST choose_best_model
# ============================================================

def test_choose_best_model_returns_lowest_rmse_mae():
    models_info = {
        "models": [
            {
                "metrics": {"RMSE": 2.0, "MAE": 1.0},
                "trained_at": "2025-12-01 10:00:00"
            },
            {
                "metrics": {"RMSE": 1.5, "MAE": 0.9},
                "trained_at": "2025-12-02 10:00:00"
            },
            {
                "metrics": {"RMSE": 1.5, "MAE": 0.8},
                "trained_at": "2025-12-01 11:00:00"
            },
        ]
    }

    best = choose_best_model(models_info)

    assert best["metrics"]["RMSE"] == 1.5
    assert best["metrics"]["MAE"] == 0.8


def test_choose_best_model_same_metrics_choose_newest():
    models_info = {
        "models": [
            {
                "metrics": {"RMSE": 1.0, "MAE": 1.0},
                "trained_at": "2025-11-01 10:00:00"
            },
            {
                "metrics": {"RMSE": 1.0, "MAE": 1.0},
                "trained_at": "2025-11-03 10:00:00"   # newest
            },
            {
                "metrics": {"RMSE": 1.0, "MAE": 1.0},
                "trained_at": "2025-11-02 10:00:00"
            },
        ]
    }

    best = choose_best_model(models_info)

    assert best["trained_at"] == "2025-11-03 10:00:00"


def test_choose_best_model_single_entry():
    models_info = {
        "models": [
            {
                "metrics": {"RMSE": 0.5, "MAE": 0.3},
                "trained_at": "2025-10-01 10:00:00"
            }
        ]
    }

    best = choose_best_model(models_info)
    assert best["metrics"]["RMSE"] == 0.5
    assert best["metrics"]["MAE"] == 0.3


def test_pre_process_X_pred_basic():
    df = pd.DataFrame({
        "semana_año": ["2025-10", "2025-11"],
        "demanda_pacientes": [10, 20],
        "complejidad": ["Alta", "Alta"],
        "temp": [30, 31],
        "humedad": [70, 75]
    })

    feature_names = ["año", "semana", "semana_continua", "temp"]

    X = pre_process_X_pred(df, feature_names)

    # Columns correct
    assert list(X.columns) == feature_names

    # Feature engineering correct
    assert X["año"].iloc[0] == 2025
    assert X["semana"].iloc[0] == 10
    assert pytest.approx(X["semana_continua"].iloc[0], rel=1e-6) == 2025.10

    # Check no deleted columns remain
    assert "demanda_pacientes" not in X.columns
    assert "complejidad" not in X.columns
    assert "semana_año" not in X.columns


def test_pre_process_X_pred_missing_feature_raises():
    df = pd.DataFrame({
        "semana_año": ["2025-10"],
        "demanda_pacientes": [10],
        "complejidad": ["Alta"],
        "temp": [30]
    })

    # feature name not present after preprocessing
    feature_names = ["año", "semana", "missing_feature"]

    with pytest.raises(KeyError):
        pre_process_X_pred(df, feature_names)


# ============================================================
# TEST predict_prophet_model
# ============================================================

def test_predict_prophet_model_basic():
    # Fake Prophet-like model
    class FakeModel:
        def make_future_dataframe(self, periods, freq):
            return pd.DataFrame({"ds": pd.date_range("2025-01-01", periods=periods)})

        def predict(self, future):
            n = len(future)
            return pd.DataFrame({
                "ds": future["ds"],
                "yhat": np.arange(n) + 10.0,
                "yhat_lower": np.arange(n) + 9.0,
                "yhat_upper": np.arange(n) + 11.0,
            })

    model = FakeModel()
    res = predict_prophet_model(model, periods=3)

    assert len(res) == 3
    assert list(res.columns) == ["ds", "yhat", "yhat_lower", "yhat_upper"]

    # Check the values appear in the tail (since tail(periods))
    assert res["yhat"].iloc[-1] == 12.0
    assert res["yhat_lower"].iloc[0] == 9.0


def test_predict_prophet_model_zero_periods():
    model = MagicMock()

    # Simulate behavior of a Prophet model but with 0 periods
    model.make_future_dataframe.return_value = pd.DataFrame({"ds": []})
    model.predict.return_value = pd.DataFrame({
        "ds": [],
        "yhat": [],
        "yhat_lower": [],
        "yhat_upper": []
    })

    res = predict_prophet_model(model, periods=0)
    # Empty dataframe expected
    assert res.empty