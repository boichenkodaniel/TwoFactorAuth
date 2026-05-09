import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_and_login_flow():
    """Test registration and login flow with mocked services"""
    with patch("app.models.user.redis_client") as mock_redis:
        # Track call count to return different values for registration vs login
        call_count = [0]
        
        def logging_get_json(key):
            call_count[0] += 1
            if key.startswith("email_index:"):
                # First call - registration (None), second call - login (user_123)
                if call_count[0] == 1:
                    return None  # Registration - user doesn't exist
                else:
                    return "user_123"  # Login - user exists
            elif key.startswith("user:"):
                return {"id": "user_123", "email": "test@example.com", "password_hash": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW", "totp_secret": None}
            return None
        
        mock_redis.get_json.side_effect = logging_get_json
        mock_redis.set_json.return_value = True

        # Register
        response = client.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "password123"},
        )
        assert response.status_code == 200

        # Login - need to mock bcrypt.checkpw
        with patch("bcrypt.checkpw", return_value=True):
            login_response = client.post(
                "/auth/login",
                json={"email": "test@example.com", "password": "password123"},
            )
            assert login_response.status_code == 200
            assert login_response.json()["status"] == "2fa_required"


def test_totp_flow():
    """Test TOTP setup and verify flow"""
    with patch("app.models.user.redis_client") as mock_redis, \
         patch("app.api.totp.TOTPService") as mock_totp, \
         patch("app.api.totp.generate_qr_code_data_url", return_value="data:image/png;base64,test"):
        
        # After setup, user will have totp_secret
        def totp_get_json(key):
            if key.startswith("email_index:"):
                return "user_123"
            elif key.startswith("user:"):
                # After setup, the user has TESTSECRET
                return {"id": "user_123", "email": "test@example.com", "password_hash": "hash", "totp_secret": "TESTSECRET"}
            return None
        
        mock_redis.get_json.side_effect = totp_get_json
        mock_redis.set_json.return_value = True
        mock_totp.generate_secret.return_value = "TESTSECRET"
        mock_totp.build_provisioning_uri.return_value = "otpauth://totp/test"
        mock_totp.verify_totp.return_value = True

        # Setup TOTP
        setup_response = client.post("/2fa/totp/setup?user_id=user_123")
        assert setup_response.status_code == 200
        assert setup_response.json()["secret"] == "TESTSECRET"

        # Verify TOTP
        verify_response = client.post(
            "/2fa/totp/verify",
            json={"user_id": "user_123", "code": "123456"},
        )
        assert verify_response.status_code == 200
        assert verify_response.json()["valid"] is True


def test_device_registration():
    """Test device registration"""
    with patch("app.models.user.redis_client") as mock_redis, \
         patch("app.api.device.redis_client") as mock_device_redis, \
         patch("app.api.device.verify_password") as mock_verify:
        
        def device_get_json(key):
            if key.startswith("email_index:"):
                return "user_123"
            elif key.startswith("user:"):
                return {"id": "user_123", "email": "test@example.com", "password_hash": "hash", "totp_secret": None}
            return None
        
        mock_redis.get_json.side_effect = device_get_json
        mock_device_redis.set_json.return_value = True
        mock_verify.return_value = True

        response = client.post(
            "/device/register",
            json={
                "email": "test@example.com",
                "password": "password123",
                "fcm_token": "fcm_token_abc",
            },
        )
        assert response.status_code == 200


def test_push_auth_flow():
    """Test push authentication flow"""
    with patch("app.models.user.redis_client") as mock_redis, \
         patch("app.api.push.redis_client") as mock_push_redis, \
         patch("app.api.push.LoginRequest") as mock_login_request, \
         patch("app.api.push.PushService") as mock_push_service:
        
        def push_get_json(key):
            if key.startswith("email_index:"):
                return "user_123"
            elif key.startswith("user:"):
                return {"id": "user_123", "email": "test@example.com", "password_hash": "hash", "totp_secret": None}
            return None
        
        mock_redis.get_json.side_effect = push_get_json
        mock_push_redis.get_json.return_value = {"fcm_token": "token123"}
        
        mock_request_instance = MagicMock()
        mock_request_instance.request_id = "req_123"
        mock_request_instance.approve.return_value = True
        mock_login_request.create_request.return_value = mock_request_instance
        mock_login_request.get_request.return_value = mock_request_instance
        mock_push_service.send_push_notification.return_value = True

        # Request push
        push_response = client.post(
            "/2fa/push/request",
            json={"user_id": "user_123"},
        )
        assert push_response.status_code == 200

        # Approve
        approve_response = client.post(
            "/2fa/push/approve",
            json={"request_id": "req_123"},
        )
        assert approve_response.status_code == 200
        assert approve_response.json()["status"] == "approved"
