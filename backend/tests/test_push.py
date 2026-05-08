import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_request_push_success():
    with patch("app.api.push.User") as mock_user:
        mock_user_instance = MagicMock()
        mock_user_instance.id = "user_123"
        mock_user.get_user_by_id.return_value = mock_user_instance

        with patch("app.api.push.LoginRequest") as mock_login_request:
            mock_request_instance = MagicMock()
            mock_request_instance.request_id = "req_123"
            mock_login_request.create_request.return_value = mock_request_instance

            with patch("app.api.push.redis_client") as mock_redis:
                mock_redis.get_json.return_value = {"fcm_token": "token123"}

                with patch("app.api.push.PushService") as mock_push:
                    mock_push.send_push_notification.return_value = True

                    response = client.post("/2fa/push/request", json={"user_id": "user_123"})

                    assert response.status_code == 200
                    data = response.json()
                    assert "request_id" in data
                    assert data["status"] == "pending"


def test_request_push_user_not_found():
    with patch("app.api.push.User") as mock_user:
        mock_user.get_user_by_id.return_value = None

        response = client.post("/2fa/push/request", json={"user_id": "nonexistent"})

        assert response.status_code == 404


def test_approve_push_success():
    with patch("app.api.push.LoginRequest") as mock_login_request:
        mock_request_instance = MagicMock()
        mock_request_instance.approve.return_value = True
        mock_login_request.get_request.return_value = mock_request_instance

        response = client.post("/2fa/push/approve", json={"request_id": "req_123"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"


def test_approve_push_not_found():
    with patch("app.api.push.LoginRequest") as mock_login_request:
        mock_login_request.get_request.return_value = None

        response = client.post("/2fa/push/approve", json={"request_id": "nonexistent"})

        assert response.status_code == 404


def test_deny_push_success():
    with patch("app.api.push.LoginRequest") as mock_login_request:
        mock_request_instance = MagicMock()
        mock_request_instance.deny.return_value = True
        mock_login_request.get_request.return_value = mock_request_instance

        response = client.post("/2fa/push/deny", json={"request_id": "req_123"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "denied"


def test_deny_push_not_found():
    with patch("app.api.push.LoginRequest") as mock_login_request:
        mock_login_request.get_request.return_value = None

        response = client.post("/2fa/push/deny", json={"request_id": "nonexistent"})

        assert response.status_code == 404
