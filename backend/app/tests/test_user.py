import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from app.models.user import User, UserRole 


@pytest.fixture
def mock_redis():
    """Mock del cliente Redis."""
    with patch("app.models.user.get_redis_client") as mock_get:
        redis = MagicMock()
        mock_get.return_value = redis
        yield redis


def test_user_create_success(mock_redis):
    mock_redis.exists.return_value = False

    user = User.create(
        email="test@example.com",
        name="Test User",
        role=UserRole.ADMIN
    )

    assert user.email == "test@example.com"
    assert user.name == "Test User"
    assert user.role == UserRole.ADMIN
    assert isinstance(user.created_at, datetime)
    assert isinstance(user.updated_at, datetime)

    mock_redis.exists.assert_called_once_with("user:test@example.com")
    mock_redis.hset.assert_called_once()
    mock_redis.sadd.assert_called_once_with("users:all", "test@example.com")


def test_user_create_duplicate(mock_redis):
    mock_redis.exists.return_value = True

    with pytest.raises(ValueError):
        User.create("dup@example.com", "Dup User")

    mock_redis.exists.assert_called_once_with("user:dup@example.com")


def test_user_save(mock_redis):
    user = User(
        email="test@example.com",
        name="Test User",
        role=UserRole.USER,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    user.save()

    mock_redis.hset.assert_called_once()
    mock_redis.sadd.assert_called_once_with("users:all", "test@example.com")

def test_user_get_success(mock_redis):
    mock_redis.hgetall.return_value = {
        "email": "test@example.com",
        "name": "User",
        "role": "user",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    user = User.get("test@example.com")
    assert user is not None
    assert user.email == "test@example.com"
    assert user.role == UserRole.USER


def test_user_get_not_found(mock_redis):
    mock_redis.hgetall.return_value = {}

    user = User.get("missing@example.com")
    assert user is None


def test_user_list_all(mock_redis):
    # Members set
    mock_redis.smembers.return_value = {"a@example.com", "b@example.com"}

    # Datos hgetall por usuario
    mock_redis.hgetall.side_effect = [
        {
            "email": "a@example.com",
            "name": "A",
            "role": "user",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        },
        {
            "email": "b@example.com",
            "name": "B",
            "role": "admin",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        },
    ]

    users = User.list_all()

    assert len(users) == 2
    assert users[0].email in ["a@example.com", "b@example.com"]
    assert users[1].email in ["a@example.com", "b@example.com"]

def test_user_update(mock_redis):
    user = User(
        email="test@example.com",
        name="Old",
        role=UserRole.USER,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    user.update(name="New Name", role=UserRole.ADMIN)

    assert user.name == "New Name"
    assert user.role == UserRole.ADMIN
    mock_redis.hset.assert_called_once()
    mock_redis.sadd.assert_called_once_with("users:all", "test@example.com")


def test_user_delete(mock_redis):
    user = User(
        email="delete@example.com",
        name="To Delete",
        role=UserRole.USER,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    user.delete()

    mock_redis.delete.assert_called_once_with("user:delete@example.com")
    mock_redis.srem.assert_called_once_with("users:all", "delete@example.com")
