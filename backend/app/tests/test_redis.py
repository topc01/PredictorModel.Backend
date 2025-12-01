import pytest
from unittest.mock import patch, MagicMock, AsyncMock

import app.core.redis as redis_client_module


@pytest.fixture(autouse=True)
def reset_clients():
    """Resetea los singletons antes de cada test."""
    redis_client_module._redis_client = None
    redis_client_module._async_redis_client = None
    yield
    redis_client_module._redis_client = None
    redis_client_module._async_redis_client = None


# -----------------------------------------------------------
# 1) Test: cliente sync se crea correctamente
# -----------------------------------------------------------
@patch("app.core.redis.redis.from_url")
def test_get_redis_client_creates_instance(mock_from_url):
    mock_instance = MagicMock()
    mock_from_url.return_value = mock_instance

    client = redis_client_module.get_redis_client()

    mock_from_url.assert_called_once()
    assert client is mock_instance
    assert redis_client_module._redis_client is mock_instance


# -----------------------------------------------------------
# 2) Test: cliente sync retorna el singleton sin recrear
# -----------------------------------------------------------
@patch("app.core.redis.redis.from_url")
def test_get_redis_client_singleton(mock_from_url):
    mock_instance = MagicMock()
    mock_from_url.return_value = mock_instance

    first = redis_client_module.get_redis_client()
    second = redis_client_module.get_redis_client()

    mock_from_url.assert_called_once()  # solo una vez
    assert first is second


# -----------------------------------------------------------
# 3) Test: cierre de cliente sync
# -----------------------------------------------------------
def test_close_redis_client():
    fake_client = MagicMock()
    redis_client_module._redis_client = fake_client

    redis_client_module.close_redis_client()

    fake_client.close.assert_called_once()
    assert redis_client_module._redis_client is None


# -----------------------------------------------------------
# 4) Test: cliente async se crea correctamente
# -----------------------------------------------------------
@patch("app.core.redis.aioredis.from_url")
@pytest.mark.asyncio
async def test_get_async_redis_client_creates(mock_from_url):
    mock_instance = AsyncMock()
    mock_from_url.return_value = mock_instance

    client = await redis_client_module.get_async_redis_client()

    mock_from_url.assert_called_once()
    assert client is mock_instance
    assert redis_client_module._async_redis_client is mock_instance


# -----------------------------------------------------------
# 5) Test: async singleton no se recrea
# -----------------------------------------------------------
@patch("app.core.redis.aioredis.from_url")
@pytest.mark.asyncio
async def test_get_async_redis_client_singleton(mock_from_url):
    mock_instance = AsyncMock()
    mock_from_url.return_value = mock_instance

    first = await redis_client_module.get_async_redis_client()
    second = await redis_client_module.get_async_redis_client()

    mock_from_url.assert_called_once()
    assert first is second


# -----------------------------------------------------------
# 6) Test: cierre async client
# -----------------------------------------------------------
@pytest.mark.asyncio
async def test_close_async_redis_client():
    fake_async = AsyncMock()
    redis_client_module._async_redis_client = fake_async

    await redis_client_module.close_async_redis_client()

    fake_async.aclose.assert_called_once()
    assert redis_client_module._async_redis_client is None
