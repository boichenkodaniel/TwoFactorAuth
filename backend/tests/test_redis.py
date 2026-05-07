import pytest
from unittest.mock import MagicMock, patch
from app.storage.redis_client import RedisClient


@pytest.fixture
def mock_redis():
    with patch("app.storage.redis_client.redis.Redis") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance


def test_set_json(mock_redis):
    client = RedisClient()
    client._client = mock_redis
    mock_redis.set.return_value = True

    result = client.set_json("test_key", {"name": "test"})

    assert result is True
    mock_redis.set.assert_called_once()


def test_get_json(mock_redis):
    client = RedisClient()
    client._client = mock_redis
    mock_redis.get.return_value = '{"name": "test"}'

    result = client.get_json("test_key")

    assert result == {"name": "test"}
    mock_redis.get.assert_called_once_with("test_key")


def test_get_json_not_found(mock_redis):
    client = RedisClient()
    client._client = mock_redis
    mock_redis.get.return_value = None

    result = client.get_json("nonexistent_key")

    assert result is None


def test_delete(mock_redis):
    client = RedisClient()
    client._client = mock_redis
    mock_redis.delete.return_value = 1

    result = client.delete("test_key")

    assert result is True
    mock_redis.delete.assert_called_once_with("test_key")


def test_exists(mock_redis):
    client = RedisClient()
    client._client = mock_redis
    mock_redis.exists.return_value = 1

    result = client.exists("test_key")

    assert result is True
