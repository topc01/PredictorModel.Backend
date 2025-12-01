import os
import json
import joblib
import pytest
from unittest.mock import patch, MagicMock
from app.utils.version import VersionManager


@pytest.fixture
def mock_mapper():
    """Mockea las complejidades para tener un entorno controlado."""
    with patch("app.utils.version.ComplexityMapper.get_all_labels") as m:
        m.return_value = ["Alta", "Baja"]
        yield


@pytest.fixture
def version_manager(tmp_path, mock_mapper, monkeypatch):
    """VersionManager en modo local con base_dir aislado."""
    monkeypatch.setenv("ENV", "local")

    # Interceptar base_dir para enviar todo a un tmp_path
    vm = VersionManager(env="local", s3_bucket=None)
    vm.base_dir = str(tmp_path / "models")

    # Reemplazar filename
    vm.filename = f"{vm.base_dir}/active_versions.json"
    vm.path.base_dir = vm.base_dir

    # Crear archivo inicial
    vm._create_version_manager()

    return vm


# -------------------------------------------------------------------
# TEST: creación del archivo active_versions.json
# -------------------------------------------------------------------

def test_create_version_manager_file(version_manager):
    assert os.path.exists(version_manager.filename)

    with open(version_manager.filename) as f:
        data = json.load(f)

    assert "Alta" in data
    assert "Baja" in data
    assert data["Alta"]["version"] == ""


# -------------------------------------------------------------------
# TEST: guardar un modelo
# -------------------------------------------------------------------

def test_save_model(version_manager):
    dummy_model = {"x": 1}
    metadata = {"complexity": "Alta"}

    result = version_manager.save_model(dummy_model, metadata)

    version = result["version"]
    model_path = result["path"]
    metadata_path = version_manager.path("Alta", version).metadata

    assert os.path.exists(model_path)
    assert os.path.exists(metadata_path)

    loaded = joblib.load(model_path)
    assert loaded == dummy_model

    with open(metadata_path) as f:
        md = json.load(f)
    assert md["complexity"] == "Alta"
    assert md["version"] == version


# -------------------------------------------------------------------
# TEST: cargar un modelo por versión
# -------------------------------------------------------------------

def test_load_model(version_manager):
    dummy_model = {"y": 2}
    metadata = {"complexity": "Baja"}

    result = version_manager.save_model(dummy_model, metadata)
    version = result["version"]

    loaded = version_manager.get_model("Baja")
    assert loaded == dummy_model


# -------------------------------------------------------------------
# TEST: get_complexity_versions
# -------------------------------------------------------------------

def test_get_complexity_versions(version_manager):
    version_manager.save_model({"a": 1}, {"complexity": "Alta"})
    version_manager.save_model({"b": 2}, {"complexity": "Alta"})

    versions = version_manager.get_complexity_versions("Alta")
    assert len(versions) == 1
    assert all("complexity" in v for v in versions)


# -------------------------------------------------------------------
# TEST: latest version
# -------------------------------------------------------------------

def test_get_latest_version(version_manager):
    version_manager.save_model({"a": 1}, {"complexity": "Alta"})
    v2 = version_manager.save_model({"b": 2}, {"complexity": "Alta"})

    latest = version_manager.get_latest_version("Alta")
    assert latest == v2["version"]


# -------------------------------------------------------------------
# TEST: active version (set / get)
# -------------------------------------------------------------------

def test_set_and_get_active_version(version_manager):
    v = version_manager.save_model({"x": 10}, {"complexity": "Baja"})
    version = v["version"]

    version_manager.set_active_version("Baja", version)

    active = version_manager.get_active_version("Baja")
    assert active == version


# -------------------------------------------------------------------
# TEST: get_model con base model fallback
# -------------------------------------------------------------------

def test_get_base_model(version_manager):
    base_path = version_manager.path("Alta").base_model

    os.makedirs(os.path.dirname(base_path), exist_ok=True)
    joblib.dump({"base": True}, base_path)

    loaded = version_manager.get_model("Alta")
    assert loaded == {"base": True}


# -------------------------------------------------------------------
# TEST: base metrics loading
# -------------------------------------------------------------------

def test_get_base_metrics(version_manager):
    metrics_path = version_manager.path("Baja").base_metrics_file

    os.makedirs(os.path.dirname(metrics_path), exist_ok=True)
    with open(metrics_path, "w") as f:
        json.dump({"mse": 10}, f)

    metrics = version_manager.get_base_metrics("Baja")
    assert metrics == {"mse": 10}


def test_get_base_metrics_not_found(version_manager):
    metrics = version_manager.get_base_metrics("Alta")
    assert metrics is None


# -------------------------------------------------------------------
# TEST: get_versions y get_active_versions
# -------------------------------------------------------------------

def test_get_versions(version_manager):
    version_manager.save_model({"a": 1}, {"complexity": "Alta"})

    versions = version_manager.get_versions()
    assert "Alta" in versions
    assert isinstance(versions["Alta"], list)


def test_get_active_versions(version_manager):
    v = version_manager.save_model({"a": 1}, {"complexity": "Baja"})
    version_manager.set_active_version("Baja", v["version"])

    active = version_manager.get_active_versions()
    assert active["Baja"] == v["version"]


# -------------------------------------------------------------------
# TEST: get_feature_names
# -------------------------------------------------------------------

def test_get_feature_names(version_manager):
    path = version_manager.path().feature_names_file
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(["f1", "f2"], path)

    names = version_manager.get_feature_names()
    assert names == ["f1", "f2"]


def test_get_feature_names_missing(version_manager):
    with pytest.raises(FileNotFoundError):
        version_manager.get_feature_names()
