import time

import pytest
import pyotp
import requests
from requests.auth import HTTPBasicAuth

BASE = "http://localhost:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"


def _server_available() -> bool:
    try:
        return requests.get(f"{BASE}/health", timeout=1).status_code == 200
    except Exception:
        return False


SKIP_REASON = "Backend server is not running on localhost:8000"


@pytest.mark.skipif(not _server_available(), reason=SKIP_REASON)
def test_register_user():
    email = f"test{int(time.time())}@example.com"
    response = requests.post(
        f"{BASE}/auth/register",
        json={"email": email, "password": "testpass123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "user_id" in data
    pytest.shared_user_id = data["user_id"]
    pytest.shared_email = email


@pytest.mark.skipif(not _server_available(), reason=SKIP_REASON)
def test_login_requires_2fa():
    response = requests.post(
        f"{BASE}/auth/login",
        json={"email": pytest.shared_email, "password": "testpass123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "2fa_required"
    assert data["user_id"] == pytest.shared_user_id


@pytest.mark.skipif(not _server_available(), reason=SKIP_REASON)
def test_setup_totp():
    response = requests.post(
        f"{BASE}/2fa/totp/setup",
        params={"user_id": pytest.shared_user_id},
    )
    assert response.status_code == 200
    data = response.json()
    assert "secret" in data
    pytest.shared_totp_secret = data["secret"]


@pytest.mark.skipif(not _server_available(), reason=SKIP_REASON)
def test_verify_totp():
    totp = pyotp.TOTP(pytest.shared_totp_secret)
    code = totp.now()
    response = requests.post(
        f"{BASE}/2fa/totp/verify",
        json={"user_id": pytest.shared_user_id, "code": code},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True


@pytest.mark.skipif(not _server_available(), reason=SKIP_REASON)
def test_register_device():
    response = requests.post(
        f"{BASE}/device/register",
        json={
            "email": pytest.shared_email,
            "password": "testpass123",
            "fcm_token": "test_fcm_token_12345",
        },
    )
    assert response.status_code == 200


@pytest.mark.skipif(not _server_available(), reason=SKIP_REASON)
def test_unregister_device():
    response = requests.post(
        f"{BASE}/device/unregister",
        json={"user_id": pytest.shared_user_id},
    )
    assert response.status_code == 200

    response = requests.post(
        f"{BASE}/device/register",
        json={
            "email": pytest.shared_email,
            "password": "testpass123",
            "fcm_token": "test_fcm_token_12345",
        },
    )
    assert response.status_code == 200


@pytest.mark.skipif(not _server_available(), reason=SKIP_REASON)
def test_list_devices():
    response = requests.get(f"{BASE}/device/list")
    assert response.status_code == 200
    data = response.json()
    assert "devices" in data


@pytest.mark.skipif(not _server_available(), reason=SKIP_REASON)
def test_request_push():
    response = requests.post(
        f"{BASE}/2fa/push/request",
        json={"user_id": pytest.shared_user_id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    pytest.shared_request_id = data["request_id"]


@pytest.mark.skipif(not _server_available(), reason=SKIP_REASON)
def test_push_status_pending():
    response = requests.get(
        f"{BASE}/2fa/push/status/{pytest.shared_request_id}",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "pending"


@pytest.mark.skipif(not _server_available(), reason=SKIP_REASON)
def test_approve_push():
    response = requests.post(
        f"{BASE}/2fa/push/approve",
        json={"request_id": pytest.shared_request_id},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


@pytest.mark.skipif(not _server_available(), reason=SKIP_REASON)
def test_push_status_approved():
    response = requests.get(
        f"{BASE}/2fa/push/status/{pytest.shared_request_id}",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


@pytest.mark.skipif(not _server_available(), reason=SKIP_REASON)
def test_admin_panel():
    response = requests.get(
        f"{BASE}/admin",
        auth=HTTPBasicAuth(ADMIN_USERNAME, ADMIN_PASSWORD),
    )
    assert response.status_code == 200
    assert len(response.text) > 0


@pytest.mark.skipif(not _server_available(), reason=SKIP_REASON)
def test_qr_code_page():
    response = requests.get(
        f"{BASE}/2fa/totp/setup/{pytest.shared_user_id}",
    )
    assert response.status_code == 200
    assert len(response.text) > 0
