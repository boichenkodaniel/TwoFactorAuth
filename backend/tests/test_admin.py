from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_admin_requires_auth():
    with patch.dict("os.environ", {"ADMIN_USERNAME": "admin", "ADMIN_PASSWORD": "secret"}):
        response = client.get("/admin")
        assert response.status_code == 401


def test_docs_requires_auth():
    with patch.dict("os.environ", {"ADMIN_USERNAME": "admin", "ADMIN_PASSWORD": "secret"}):
        response = client.get("/docs")
        assert response.status_code == 401


def test_admin_with_auth():
    with patch.dict("os.environ", {"ADMIN_USERNAME": "admin", "ADMIN_PASSWORD": "secret"}):
        with patch("app.api.admin.redis_client") as mock_redis:
            mock_redis_instance = mock_redis.get_redis.return_value
            mock_redis_instance.scan_iter.side_effect = [[], [], []]

            response = client.get("/admin", auth=("admin", "secret"))

        assert response.status_code == 200
        assert "2FA Admin Panel" in response.text


def test_admin_unregister_device_redirects():
    with patch.dict("os.environ", {"ADMIN_USERNAME": "admin", "ADMIN_PASSWORD": "secret"}):
        with patch("app.api.admin.User") as mock_user, patch("app.api.admin.redis_client") as mock_redis:
            mock_user.get_user_by_id.return_value = object()
            mock_redis.delete.return_value = True

            response = client.post(
                "/admin/devices/user_123/unregister",
                auth=("admin", "secret"),
                follow_redirects=False,
            )

        assert response.status_code == 303
        assert "Device+unregistered+successfully" in response.headers["location"]
