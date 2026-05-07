import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_setup_totp_success():
    with patch("app.api.totp.User") as mock_user:
        mock_user_instance = MagicMock()
        mock_user_instance.id = "user_123"
        mock_user_instance.email = "user@example.com"
        mock_user_instance.totp_secret = None
        mock_user.get_user_by_id.return_value = mock_user_instance

        with patch("app.api.totp.TOTPService") as mock_totp, patch(
            "app.api.totp.generate_qr_code_data_url",
            return_value="data:image/png;base64,test",
        ):
            mock_totp.generate_secret.return_value = "TESTSECRET123"
            mock_totp.build_provisioning_uri.return_value = "otpauth://totp/test"

            response = client.post("/2fa/totp/setup?user_id=user_123")

            assert response.status_code == 200
            data = response.json()
            assert "secret" in data
            assert data["secret"] == "TESTSECRET123"
            assert data["uri"].startswith("otpauth://totp/")
            assert data["qr_code_data_url"].startswith("data:image/png;base64,")
            assert data["account_name"]


def test_setup_totp_user_not_found():
    with patch("app.api.totp.User") as mock_user:
        mock_user.get_user_by_id.return_value = None

        response = client.post("/2fa/totp/setup?user_id=nonexistent")

        assert response.status_code == 404


def test_verify_totp_success():
    with patch("app.api.totp.User") as mock_user:
        mock_user_instance = MagicMock()
        mock_user_instance.id = "user_123"
        mock_user_instance.totp_secret = "TESTSECRET123"
        mock_user.get_user_by_id.return_value = mock_user_instance

        with patch("app.api.totp.TOTPService") as mock_totp:
            mock_totp.verify_totp.return_value = True

            response = client.post(
                "/2fa/totp/verify",
                json={"user_id": "user_123", "code": "123456"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True


def test_verify_totp_invalid_code():
    with patch("app.api.totp.User") as mock_user:
        mock_user_instance = MagicMock()
        mock_user_instance.id = "user_123"
        mock_user_instance.totp_secret = "TESTSECRET123"
        mock_user.get_user_by_id.return_value = mock_user_instance

        with patch("app.api.totp.TOTPService") as mock_totp:
            mock_totp.verify_totp.return_value = False

            response = client.post(
                "/2fa/totp/verify",
                json={"user_id": "user_123", "code": "000000"},
            )

            assert response.status_code == 401


def test_verify_totp_user_not_found():
    with patch("app.api.totp.User") as mock_user:
        mock_user.get_user_by_id.return_value = None

        response = client.post(
            "/2fa/totp/verify",
            json={"user_id": "nonexistent", "code": "123456"},
        )

        assert response.status_code == 404


def test_verify_totp_not_configured():
    with patch("app.api.totp.User") as mock_user:
        mock_user_instance = MagicMock()
        mock_user_instance.id = "user_123"
        mock_user_instance.totp_secret = None
        mock_user.get_user_by_id.return_value = mock_user_instance

        response = client.post(
            "/2fa/totp/verify",
            json={"user_id": "user_123", "code": "123456"},
        )

        assert response.status_code == 400


def test_setup_totp_qr_page():
    with patch("app.api.totp.User") as mock_user, patch(
        "app.api.totp.generate_qr_code_data_url",
        return_value="data:image/png;base64,test",
    ):
        mock_user_instance = MagicMock()
        mock_user_instance.id = "user_123"
        mock_user_instance.email = "user@example.com"
        mock_user_instance.totp_secret = "TESTSECRET123"
        mock_user.get_user_by_id.return_value = mock_user_instance

        with patch("app.api.totp.TOTPService") as mock_totp:
            mock_totp.build_provisioning_uri.return_value = "otpauth://totp/test"
            response = client.get("/2fa/totp/setup/user_123")

        assert response.status_code == 200
        assert "Authy" in response.text
