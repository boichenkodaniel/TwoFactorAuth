import pytest
from unittest.mock import MagicMock, patch
from app.services.login_request_service import LoginRequest, LoginRequestStatus


@pytest.fixture
def mock_redis_client():
    with patch("app.services.login_request_service.redis_client") as mock:
        yield mock


def test_create_request(mock_redis_client):
    mock_redis_client.set_json.return_value = True

    request = LoginRequest.create_request(user_id="user_123")

    assert request.user_id == "user_123"
    assert request.status == LoginRequestStatus.PENDING
    assert request.request_id is not None
    mock_redis_client.set_json.assert_called_once()


def test_approve_request(mock_redis_client):
    mock_redis_client.set_json.return_value = True

    request = LoginRequest(user_id="user_123", request_id="req_123")
    result = request.approve()

    assert result is True
    assert request.status == LoginRequestStatus.APPROVED
    mock_redis_client.set_json.assert_called_once()


def test_deny_request(mock_redis_client):
    mock_redis_client.set_json.return_value = True

    request = LoginRequest(user_id="user_123", request_id="req_123")
    result = request.deny()

    assert result is True
    assert request.status == LoginRequestStatus.DENIED
    mock_redis_client.set_json.assert_called_once()


def test_get_request_status(mock_redis_client):
    mock_redis_client.get_json.return_value = {
        "request_id": "req_123",
        "user_id": "user_123",
        "status": "pending",
    }

    request = LoginRequest.get_request("req_123")

    assert request is not None
    assert request.user_id == "user_123"
    assert request.status == LoginRequestStatus.PENDING


def test_get_request_not_found(mock_redis_client):
    mock_redis_client.get_json.return_value = None

    request = LoginRequest.get_request("nonexistent")

    assert request is None


def test_get_request_status_enum(mock_redis_client):
    mock_redis_client.get_json.return_value = {
        "request_id": "req_123",
        "user_id": "user_123",
        "status": "approved",
    }

    request = LoginRequest.get_request("req_123")

    assert request.status == LoginRequestStatus.APPROVED
