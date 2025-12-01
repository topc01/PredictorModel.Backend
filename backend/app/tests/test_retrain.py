import os
import json
import pandas as pd
import pytest
import numpy as np

from app.retrain import retrain as retrain_module


def test_prepare_data_prophet_success():
    df = pd.DataFrame({
        'semana_año': ['2025-01', '2025-02'],
        'demanda_pacientes': [10, 15]
    })

    out = retrain_module.prepare_data_prophet(df)

    assert 'ds' in out.columns and 'y' in out.columns
    assert len(out) == 2
    assert pd.api.types.is_datetime64_any_dtype(out['ds'])


def test_prepare_data_prophet_empty_raises():
    with pytest.raises(ValueError):
        retrain_module.prepare_data_prophet(pd.DataFrame())


def test_obtain_metrics_prophet():
    y_true = np.array([1.0, 2.0, 3.0])
    y_pred = np.array([1.1, 1.9, 3.2])

    metrics = retrain_module.obtain_metrics_prophet(y_true, y_pred)

    assert 'MAE' in metrics and 'R2' in metrics
    assert pytest.approx(metrics['MAE'], rel=1e-3) == float(np.mean(np.abs(y_true - y_pred)))


def test_save_prophet_model_success_and_errors(monkeypatch):
    # success path
    dummy_model = object()

    def fake_save_model(model, metadata):
        return {'version': 'v_test', 'metadata': metadata}

    monkeypatch.setattr(retrain_module, 'version_manager', type('VM', (), {'save_model': staticmethod(fake_save_model)}))

    df_prophet = pd.DataFrame({'ds': [pd.Timestamp('2025-01-01')], 'y': [1]})
    metrics = {'MAE': 0.1}

    res = retrain_module.save_prophet_model(dummy_model, metrics, 'TestComplex', df_prophet)
    assert res['version'] == 'v_test'

    # error cases
    with pytest.raises(ValueError):
        retrain_module.save_prophet_model(None, metrics, 'TestComplex', df_prophet)

    with pytest.raises(ValueError):
        retrain_module.save_prophet_model(dummy_model, ['not', 'a', 'dict'], 'TestComplex', df_prophet)

    with pytest.raises(ValueError):
        retrain_module.save_prophet_model(dummy_model, metrics, 'TestComplex', pd.DataFrame())

    with pytest.raises(ValueError):
        retrain_module.save_prophet_model(dummy_model, metrics, '', df_prophet)


def test_load_data_and_edge_cases(monkeypatch):
    # prepare a DataFrame to be returned by storage_manager.load_csv
    df = pd.DataFrame({
        'complejidad': ['A', 'B', 'A'],
        'semana_año': ['2025-01', '2025-01', '2025-02'],
        'demanda_pacientes': [5, 6, 7]
    })

    class FakeStorage:
        @staticmethod
        def load_csv(name):
            return df

    monkeypatch.setattr(retrain_module, 'storage_manager', FakeStorage)

    # Make ComplexityMapper treat label as already real name
    class FakeCM:
        @staticmethod
        def is_valid_label(x):
            return False

    monkeypatch.setattr(retrain_module, 'ComplexityMapper', FakeCM)

    res = retrain_module.load_data('A')
    assert not res.empty
    assert all(res['complejidad'] == 'A')

    # storage returns None
    class EmptyStorage:
        @staticmethod
        def load_csv(name):
            return None

    monkeypatch.setattr(retrain_module, 'storage_manager', EmptyStorage)
    with pytest.raises(ValueError):
        retrain_module.load_data('A')

    # storage returns dataframe but no matching complexity
    class NoMatchStorage:
        @staticmethod
        def load_csv(name):
            return pd.DataFrame({'complejidad': ['X'], 'semana_año': ['2025-01'], 'demanda_pacientes':[1]})

    monkeypatch.setattr(retrain_module, 'storage_manager', NoMatchStorage)
    with pytest.raises(ValueError):
        retrain_module.load_data('NonExisting')


def test_get_prophet_models_reads_metadata(tmp_path, monkeypatch):
    # change cwd to tmp_path so 'models/prophet' is created there
    monkeypatch.chdir(tmp_path)

    base = tmp_path / 'models' / 'prophet' / 'TestComplex'
    version_dir = base / 'v1'
    version_dir.mkdir(parents=True)

    metadata = {'trained_at': '2025-12-01T12:00:00', 'n_samples': 10, 'params': {'p': 1}}
    metrics = {'MAE': 0.5}

    (version_dir / 'metadata.json').write_text(json.dumps(metadata))
    (version_dir / 'metrics.json').write_text(json.dumps(metrics))

    class FakeCM:
        @staticmethod
        def is_valid_label(x):
            return False

    monkeypatch.setattr(retrain_module, 'ComplexityMapper', FakeCM)

    res = retrain_module.get_prophet_models('TestComplex')

    assert res['complexity'] == 'TestComplex'
    assert res['count'] == 1
    assert len(res['models']) == 1
    m = res['models'][0]
    assert m['version'] == 'v1'
    assert m['metrics'] == metrics
