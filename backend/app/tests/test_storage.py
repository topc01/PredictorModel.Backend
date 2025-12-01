import os
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from app.utils.storage import StorageManager, check_bucket_access, get_bucket_info

# ------------------------------
# FIXTURES
# ------------------------------

@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "col1": [1, 2, 3],
        "col2": ["a", "b", "c"]
    })


@pytest.fixture
def local_manager(tmp_path, monkeypatch):
    """StorageManager en modo local usando un directorio temporal."""
    monkeypatch.setenv("ENV", "local")

    manager = StorageManager(env="local")
    manager.base_dir = tmp_path  # Redirige data/ al tmp_path

    return manager


# ------------------------------
# TESTS LOCAL STORAGE
# ------------------------------

def test_save_csv_local(local_manager, sample_df):
    path = local_manager.save_csv(sample_df, "test.csv")

    assert os.path.exists(path)

    loaded = pd.read_csv(path)
    assert loaded.equals(sample_df)


def test_load_csv_local(local_manager, sample_df):
    path = local_manager.save_csv(sample_df, "hist.csv")

    df_loaded = local_manager.load_csv("hist.csv")
    assert df_loaded.equals(sample_df)


def test_exists_local_true(local_manager, sample_df):
    local_manager.save_csv(sample_df, "exists.csv")
    assert local_manager.exists("exists.csv")


def test_exists_local_false(local_manager):
    assert not local_manager.exists("missing.csv")


def test_load_csv_local_not_found(local_manager):
    with pytest.raises(FileNotFoundError):
        local_manager.load_csv("nope.csv")



from moto import mock_aws as mock_s3
import boto3


@pytest.fixture
def s3_manager():
    with mock_s3():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="my-test-bucket")

        manager = StorageManager(env="s3", s3_bucket="my-test-bucket")
        yield manager


def test_save_csv_s3(s3_manager, sample_df):
    uri = s3_manager.save_csv(sample_df, "file.csv")
    assert uri == "s3://my-test-bucket/file.csv"

    # Verificar que se guardó en S3
    client = boto3.client("s3")
    obj = client.get_object(Bucket="my-test-bucket", Key="file.csv")
    df_loaded = pd.read_csv(obj["Body"])

    assert df_loaded.equals(sample_df)


def test_load_csv_s3(s3_manager, sample_df):
    # Guardar manualmente en S3
    client = boto3.client("s3")
    csv_data = sample_df.to_csv(index=False)
    client.put_object(Bucket="my-test-bucket", Key="hist.csv", Body=csv_data)

    df = s3_manager.load_csv("hist.csv")
    assert df.equals(sample_df)


def test_exists_s3_true(s3_manager, sample_df):
    client = boto3.client("s3")
    client.put_object(Bucket="my-test-bucket", Key="test.csv", Body="a,b\n1,2")

    assert s3_manager.exists("test.csv")


def test_exists_s3_false(s3_manager):
    assert not s3_manager.exists("missing.csv")


def test_load_s3_missing_key(s3_manager):
    with pytest.raises(FileNotFoundError):
        s3_manager.load_csv("notfound.csv")


# ------------------------------
# MULTIPLE SAVE
# ------------------------------

def test_save_multiple_csvs(local_manager, sample_df):
    dfs = {
        "a.csv": sample_df,
        "b.csv": sample_df
    }

    paths = local_manager.save_multiple_csvs(dfs)

    assert "a.csv" in paths
    assert "b.csv" in paths
    assert local_manager.exists("a.csv")
    assert local_manager.exists("b.csv")


# ------------------------------
# TESTS check_bucket_access
# ------------------------------

def test_check_bucket_access_exists():
    with mock_s3():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="demo-bucket")

        result = check_bucket_access("demo-bucket")

        assert result["accessible"] is True
        assert result["exists"] is True
        assert result["error"] is None


def test_check_bucket_access_no_bucket():
    with mock_s3():
        result = check_bucket_access("no-bucket")

        assert result["accessible"] is False
        assert result["exists"] is False
        assert "does not exist" in result["error"].lower()


def test_check_bucket_access_forbidden():
    with mock_s3():
        with patch("boto3.client") as mock_client:
            # Simula error 403
            instance = mock_client.return_value
            err = MagicMock()
            err.response = {"Error": {"Code": "403"}}
            instance.head_bucket.side_effect = err

            resp = check_bucket_access("bucket")

            assert resp["accessible"] is True
            assert resp["exists"] is True


# ------------------------------
# TESTS get_bucket_info
# ------------------------------

def test_get_bucket_info_ok():
    with mock_s3():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="info-bucket")

        info = get_bucket_info("info-bucket")

        assert info["name"] == "info-bucket"
        assert info["region"] == "us-east-1"


def test_get_bucket_info_fail():
    with mock_s3():
        info = get_bucket_info("not-found")
        assert info is None
