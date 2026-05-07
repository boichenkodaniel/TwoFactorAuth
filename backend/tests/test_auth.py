import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_register_success():
    with patch("app.api.auth.User") as mock_user:
        mock_user_instance = MagicMock()
        mock_user_instance.id = "test_user_id"
        mock_user.create_user.return_value = mock_user_instance

        response = client.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "securepassword123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test_user_id"
        assert "message" in data


def test_register_duplicate_email():
    with patch("app.api.auth.User") as mock_user:
        mock_user.create_user.return_value = None

        response = client.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "securepassword123"},
        )

        assert response.status_code == 400
        assert "detail" in response.json()


def test_register_invalid_email():
    response = client.post(
        "/auth/register",
        json={"email": "invalid_email", "password": "securepassword123"},
    )

    assert response.status_code == 422


def test_login_success():
    with patch("app.api.auth.User") as mock_user:
        mock_user_instance = MagicMock()
        mock_user_instance.id = "test_user_id"
        mock_user_instance.password_hash = "hashed_password"
        mock_user.get_user_by_email.return_value = mock_user_instance

        with patch("app.api.auth.verify_password", return_value=True):
            response = client.post(
                "/auth/login",
                json={"email": "test@example.com", "password": "securepassword123"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "2fa_required"
            assert data["user_id"] == "test_user_id"


def test_login_invalid_password():
    with patch("app.api.auth.User") as mock_user:
        mock_user_instance = MagicMock()
        mock_user_instance.password_hash = "hashed_password"
        mock_user.get_user_by_email.return_value = mock_user_instance

        with patch("app.api.auth.verify_password", return_value=False):
            response = client.post(
                "/auth/login",
                json={"email": "test@example.com", "password": "wrongpassword"},
            )

            assert response.status_code == 401


def test_login_unknown_email():
    with patch("app.api.auth.User") as mock_user:
        mock_user.get_user_by_email.return_value = None

        response = client.post(
            "/auth/login",
            json={"email": "unknown@example.com", "password": "securepassword123"},
        )

        assert response.status_code == 401
