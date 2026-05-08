from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_register_device_success():
    with patch("app.api.device.User") as mock_user, patch("app.api.device.verify_password") as mock_verify:
        mock_user_instance = MagicMock()
        mock_user_instance.id = "user_123"
        mock_user_instance.email = "user@example.com"
        mock_user_instance.password_hash = "hash"
        mock_user.get_user_by_email.return_value = mock_user_instance
        mock_verify.return_value = True

        with patch("app.api.device.redis_client") as mock_redis:
            mock_redis.set_json.return_value = True

            response = client.post(
                "/device/register",
                json={
                    "email": "user@example.com",
                    "password": "password123",
                    "fcm_token": "fcm_token_abc123",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == "user_123"
            assert "message" in data


def test_register_device_invalid_credentials():
    with patch("app.api.device.User") as mock_user, patch("app.api.device.verify_password") as mock_verify:
        mock_user_instance = MagicMock()
        mock_user_instance.password_hash = "hash"
        mock_user.get_user_by_email.return_value = mock_user_instance
        mock_verify.return_value = False

        response = client.post(
            "/device/register",
            json={
                "email": "user@example.com",
                "password": "bad-password",
                "fcm_token": "fcm_token_abc123",
            },
        )

        assert response.status_code == 401


def test_unregister_device_success():
    with patch("app.api.device.User") as mock_user, patch("app.api.device.redis_client") as mock_redis:
        mock_user.get_user_by_id.return_value = MagicMock(id="user_123")
        mock_redis.delete.return_value = True

        response = client.post("/device/unregister", json={"user_id": "user_123"})

        assert response.status_code == 200
        assert response.json()["message"] == "Device unregistered successfully"


def test_list_devices():
    with patch("app.api.device.redis_client") as mock_redis:
        mock_redis_instance = MagicMock()
        mock_redis.get_redis.return_value = mock_redis_instance
        mock_redis_instance.scan_iter.return_value = ["device:user_123"]
        mock_redis.get_json.return_value = {
            "user_id": "user_123",
            "email": "user@example.com",
            "fcm_token": "token123",
        }

        response = client.get("/device/list")

        assert response.status_code == 200
        data = response.json()
        assert "devices" in data
        assert len(data["devices"]) > 0
