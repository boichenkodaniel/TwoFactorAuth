import pytest
from unittest.mock import MagicMock, patch
from app.models.user import User
from app.storage.redis_client import RedisClient


@pytest.fixture
def mock_redis_client():
    with patch("app.models.user.redis_client") as mock:
        yield mock


def test_create_user(mock_redis_client):
    mock_redis_client.get_json.return_value = None
    mock_redis_client.set_json.return_value = True

    user = User.create_user(email="test@example.com", password_hash="hashed_password")

    assert user is not None
    assert user.email == "test@example.com"
    assert user.password_hash == "hashed_password"
    assert user.id is not None


def test_create_user_duplicate_email(mock_redis_client):
    mock_redis_client.get_json.side_effect = [
        "existing_user_id",
        {"id": "existing_user_id", "email": "test@example.com", "password_hash": "hash", "totp_secret": None},
    ]

    user = User.create_user(email="test@example.com", password_hash="hashed_password")

    assert user is None


def test_get_user_by_email_not_found(mock_redis_client):
    mock_redis_client.get_json.return_value = None

    user = User.get_user_by_email("nonexistent@example.com")

    assert user is None


def test_get_user_by_email(mock_redis_client):
    mock_redis_client.get_json.side_effect = [
        "user_id_123",
        {"id": "user_id_123", "email": "test@example.com", "password_hash": "hash", "totp_secret": None},
    ]

    user = User.get_user_by_email("test@example.com")

    assert user is not None
    assert user.id == "user_id_123"
    assert user.email == "test@example.com"


def test_get_user_by_id_not_found(mock_redis_client):
    mock_redis_client.get_json.return_value = None

    user = User.get_user_by_id("nonexistent_id")

    assert user is None


def test_get_user_by_id(mock_redis_client):
    mock_redis_client.get_json.return_value = {
        "id": "user_id_123",
        "email": "test@example.com",
        "password_hash": "hash",
        "totp_secret": "SECRET123",
    }

    user = User.get_user_by_id("user_id_123")

    assert user is not None
    assert user.id == "user_id_123"
    assert user.totp_secret == "SECRET123"


def test_update_user(mock_redis_client):
    mock_redis_client.set_json.return_value = True

    user = User(id="user_id_123", email="test@example.com", password_hash="hash", totp_secret="NEW_SECRET")
    result = User.update_user(user)

    assert result is True
    mock_redis_client.set_json.assert_called_once()
