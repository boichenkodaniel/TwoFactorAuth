"""
Performance API Response Time Tests

Проверяет время ответа ключевых API-эндпоинтов.
Целевое время: < 200 мс для in-memory операций.
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# --- Helpers ---


def measure_response_time(method, url, **kwargs) -> tuple:
    """Выполняет запрос и возвращает (response, elapsed_ms)."""
    start = time.perf_counter()
    response = getattr(client, method)(url, **kwargs)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return response, elapsed_ms


# --- Auth Endpoints ---


class TestAuthPerformance:
    """Производительность эндпоинтов аутентификации."""

    def test_register_response_time(self):
        with patch("app.api.auth.User") as mock_user:
            mock_user_instance = MagicMock()
            mock_user_instance.id = "perf_user_1"
            mock_user.create_user.return_value = mock_user_instance

            response, elapsed_ms = measure_response_time(
                "post",
                "/auth/register",
                json={"email": "perf1@test.com", "password": "pass123"},
            )

            assert response.status_code == 200
            # First call may be slower due to initialization (bcrypt, etc.)
            assert elapsed_ms < 300, f"Register took {elapsed_ms:.2f} ms (target < 300 for first call)"

    def test_login_response_time(self):
        with patch("app.api.auth.User") as mock_user:
            mock_user_instance = MagicMock()
            mock_user_instance.id = "perf_user_2"
            mock_user_instance.password_hash = "hashed_pass"
            mock_user.get_user_by_email.return_value = mock_user_instance

            with patch("app.api.auth.verify_password", return_value=True):
                response, elapsed_ms = measure_response_time(
                    "post",
                    "/auth/login",
                    json={"email": "perf2@test.com", "password": "pass123"},
                )

                assert response.status_code == 200
                assert elapsed_ms < 200, f"Login took {elapsed_ms:.2f} ms (target < 200)"


# --- TOTP Endpoints ---


class TestTotpPerformance:
    """Производительность эндпоинтов TOTP."""

    def test_totp_setup_response_time(self):
        with patch("app.api.totp.User") as mock_user:
            mock_user_instance = MagicMock()
            mock_user_instance.id = "totp_user"
            mock_user_instance.email = "totp@test.com"
            mock_user_instance.totp_secret = None
            mock_user.get_user_by_id.return_value = mock_user_instance

            with patch("app.api.totp.TOTPService.generate_secret", return_value="JBSWY3DPEHPK3PXP"):
                with patch.object(mock_user, "update_user"):
                    response, elapsed_ms = measure_response_time(
                        "post",
                        "/2fa/totp/setup?user_id=totp_user",
                    )

                    assert response.status_code == 200
                    assert elapsed_ms < 300, f"TOTP setup took {elapsed_ms:.2f} ms (target < 300)"

    def test_totp_verify_response_time(self):
        with patch("app.api.totp.User") as mock_user:
            mock_user_instance = MagicMock()
            mock_user_instance.id = "totp_user"
            mock_user_instance.totp_secret = "JBSWY3DPEHPK3PXP"
            mock_user.get_user_by_id.return_value = mock_user_instance

            with patch("app.api.totp.TOTPService.verify_totp", return_value=True):
                response, elapsed_ms = measure_response_time(
                    "post",
                    "/2fa/totp/verify",
                    json={"user_id": "totp_user", "code": "123456"},
                )

                assert response.status_code == 200
                assert elapsed_ms < 200, f"TOTP verify took {elapsed_ms:.2f} ms (target < 200)"


# --- Device Endpoints ---


class TestDevicePerformance:
    """Производительность эндпоинтов управления устройствами."""

    def test_device_register_response_time(self):
        with patch("app.api.device.User") as mock_user:
            mock_user_instance = MagicMock()
            mock_user_instance.id = "device_user"
            mock_user_instance.password_hash = "hashed"
            mock_user.get_user_by_email.return_value = mock_user_instance

            with patch("app.api.device.verify_password", return_value=True):
                with patch("app.api.device.redis_client") as mock_redis:
                    mock_redis.set_json.return_value = True

                    response, elapsed_ms = measure_response_time(
                        "post",
                        "/device/register",
                        json={
                            "email": "device@test.com",
                            "password": "pass123",
                            "fcm_token": "test_fcm_token",
                        },
                    )

                    assert response.status_code == 200
                    assert elapsed_ms < 200, (
                        f"Device register took {elapsed_ms:.2f} ms (target < 200)"
                    )

    def test_device_list_response_time(self):
        with patch("app.api.device.redis_client") as mock_redis:
            mock_redis.get_json.return_value = {
                "user_id": "device_user",
                "email": "device@test.com",
                "fcm_token": "token",
            }

            response, elapsed_ms = measure_response_time(
                "get",
                "/device/list?user_id=device_user",
            )

            assert response.status_code == 200
            assert elapsed_ms < 150, (
                f"Device list took {elapsed_ms:.2f} ms (target < 150)"
            )


# --- Push Endpoints ---


class TestPushPerformance:
    """Производительность эндпоинтов push-аутентификации."""

    def test_push_request_response_time(self):
        with patch("app.api.push.User") as mock_user:
            mock_user_instance = MagicMock()
            mock_user_instance.id = "push_user"
            mock_user.get_user_by_id.return_value = mock_user_instance

            with patch("app.api.push.LoginRequest") as mock_lr:
                mock_request = MagicMock()
                mock_request.request_id = "req_123"
                mock_request.get_status.return_value = MagicMock(value="pending")
                mock_request.site_name = "test.com"
                mock_lr.create_request.return_value = mock_request

                with patch("app.api.push.PushService.send_push_notification"):
                    with patch("app.api.push.redis_client") as mock_redis:
                        mock_redis.get_json.return_value = {
                            "fcm_token": "test_token",
                        }

                        response, elapsed_ms = measure_response_time(
                            "post",
                            "/2fa/push/request",
                            json={"user_id": "push_user", "site_name": "test.com"},
                            headers={"referer": "https://test.com/login"},
                        )

                        assert response.status_code == 200
                        assert elapsed_ms < 300, (
                            f"Push request took {elapsed_ms:.2f} ms (target < 300)"
                        )

    def test_push_status_response_time(self):
        with patch("app.api.push.LoginRequest") as mock_lr:
            mock_request = MagicMock()
            mock_request.get_status.return_value = MagicMock(value="pending")
            mock_request.site_name = "test.com"
            mock_lr.get_request.return_value = mock_request

            response, elapsed_ms = measure_response_time(
                "get",
                "/2fa/push/status/req_123",
            )

            assert response.status_code == 200
            assert elapsed_ms < 150, (
                f"Push status took {elapsed_ms:.2f} ms (target < 150)"
            )

    def test_push_approve_response_time(self):
        with patch("app.api.push.LoginRequest") as mock_lr:
            mock_request = MagicMock()
            mock_lr.get_request.return_value = mock_request

            response, elapsed_ms = measure_response_time(
                "post",
                "/2fa/push/approve",
                json={"request_id": "req_123"},
            )

            assert response.status_code == 200
            assert elapsed_ms < 200, (
                f"Push approve took {elapsed_ms:.2f} ms (target < 200)"
            )


# --- Health Check ---


class TestHealthPerformance:
    """Производительность health-check."""

    def test_health_response_time(self):
        response, elapsed_ms = measure_response_time("get", "/health")

        assert response.status_code == 200
        assert elapsed_ms < 50, (
            f"Health check took {elapsed_ms:.2f} ms (target < 50)"
        )


# --- Summary Table ---


def test_print_performance_summary():
    """
    Выводит сводную таблицу целевых показателей производительности.
    Не является тестом assert — служит документацией.
    """
    summary = """
    ╔══════════════════════════════════════════════════════════════════════╗
    ║                    API Performance Targets                            ║
    ╠══════════════════════════════════════════════════════════════════════╣
    ║  Endpoint              │  Method  │  Target <  │  Notes              ║
    ╠══════════════════════════════════════════════════════════════════════╣
    ║  /auth/register        │  POST    │  200 ms    │  bcrypt hashing     ║
    ║  /auth/login           │  POST    │  200 ms    │  bcrypt verify      ║
    ║  /2fa/totp/setup       │  POST    │  300 ms    │  QR generation      ║
    ║  /2fa/totp/verify      │  POST    │  200 ms    │  HMAC-SHA1          ║
    ║  /device/register      │  POST    │  200 ms    │  Redis write        ║
    ║  /device/list          │  GET     │  150 ms    │  Redis read         ║
    ║  /2fa/push/request     │  POST    │  300 ms    │  FCM call (mocked)  ║
    ║  /2fa/push/status      │  GET     │  150 ms    │  Redis read         ║
    ║  /2fa/push/approve     │  POST    │  200 ms    │  Redis write        ║
    ║  /health               │  GET     │   50 ms    │  Static response    ║
    ╚══════════════════════════════════════════════════════════════════════╝
    """
    print(summary)
    assert True
