from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_request_push_includes_site_name_in_payload():
    with patch("app.api.push.User") as mock_user, patch("app.api.push.LoginRequest") as mock_login_request, patch(
        "app.api.push.redis_client"
    ) as mock_redis, patch("app.api.push.PushService") as mock_push:
        mock_user.get_user_by_id.return_value = MagicMock(id="user_123")
        mock_request_instance = MagicMock()
        mock_request_instance.request_id = "req_123"
        mock_login_request.create_request.return_value = mock_request_instance
        mock_redis.get_json.return_value = {"fcm_token": "token123"}

        response = client.post(
            "/2fa/push/request",
            headers={"origin": "https://example.com"},
            json={"user_id": "user_123"},
        )

        assert response.status_code == 200
        mock_login_request.create_request.assert_called_once_with(
            user_id="user_123",
            site_name="example.com",
        )
        _, kwargs = mock_push.send_push_notification.call_args
        assert kwargs["data"]["site_name"] == "example.com"


def test_get_push_status_returns_site_name():
    with patch("app.api.push.LoginRequest") as mock_login_request:
        mock_request = MagicMock()
        mock_request.get_status.return_value.value = "pending"
        mock_request.site_name = "example.com"
        mock_login_request.get_request.return_value = mock_request

        response = client.get("/2fa/push/status/req_123")

        assert response.status_code == 200
        assert response.json()["site_name"] == "example.com"


def test_get_pending_push_request_success():
    with patch("app.api.push.redis_client") as mock_redis:
        mock_redis_instance = mock_redis.get_redis.return_value
        mock_redis_instance.scan_iter.return_value = ["login_request:req_123"]
        mock_redis.get_json.return_value = {
            "request_id": "req_123",
            "user_id": "user_123",
            "status": "pending",
            "site_name": "example.com",
        }

        response = client.get("/2fa/push/pending/user_123")

        assert response.status_code == 200
        data = response.json()
        assert data["request_id"] == "req_123"
        assert data["site_name"] == "example.com"


def test_get_pending_push_request_not_found():
    with patch("app.api.push.redis_client") as mock_redis:
        mock_redis_instance = mock_redis.get_redis.return_value
        mock_redis_instance.scan_iter.return_value = []

        response = client.get("/2fa/push/pending/user_123")

        assert response.status_code == 404
