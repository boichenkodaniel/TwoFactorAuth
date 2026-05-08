import pytest
from unittest.mock import patch
from app.services.firebase import FirebaseService


def test_initialize_with_credentials():
    """Test Firebase initialization with credentials from env."""
    with patch.dict("os.environ", {"FIREBASE_CREDENTIALS": '{"project_id": "test"}'}):
        with patch("app.services.firebase.credentials.Certificate") as mock_cred:
            with patch("app.services.firebase.firebase_admin.initialize_app") as mock_init:
                FirebaseService._initialized = False
                FirebaseService.initialize()
                assert FirebaseService._initialized is True
                mock_init.assert_called_once()


def test_initialize_default():
    """Test Firebase initialization with default credentials."""
    with patch.dict("os.environ", {}, clear=True):
        with patch("app.services.firebase.Path.exists", return_value=False):
            with patch("app.services.firebase.firebase_admin.initialize_app") as mock_init:
                FirebaseService._initialized = False
                FirebaseService.initialize()
                assert FirebaseService._initialized is True
                mock_init.assert_called_once()


def test_initialize_with_local_service_account():
    """Test Firebase initialization with local serviceAccountKey.json fallback."""
    with patch.dict("os.environ", {}, clear=True):
        with patch("app.services.firebase.Path.exists", return_value=True):
            with patch("app.services.firebase.credentials.Certificate") as mock_cred:
                with patch("app.services.firebase.firebase_admin.initialize_app") as mock_init:
                    FirebaseService._initialized = False
                    FirebaseService.initialize()
                    assert FirebaseService._initialized is True
                    mock_cred.assert_called_once()
                    mock_init.assert_called_once()


def test_send_message():
    """Test sending FCM message."""
    with patch("app.services.firebase.messaging.send") as mock_send:
        mock_send.return_value = "message_id_123"
        FirebaseService._initialized = True

        result = FirebaseService.send_message(
            token="test_token",
            title="Test",
            body="Body",
            data={"type": "login_request"},
        )

        assert result == "message_id_123"
        mock_send.assert_called_once()


def test_send_message_without_data():
    """Test sending FCM message without data payload."""
    with patch("app.services.firebase.messaging.send") as mock_send:
        mock_send.return_value = "message_id_456"
        FirebaseService._initialized = True

        result = FirebaseService.send_message(
            token="test_token",
            title="Test",
            body="Body",
        )

        assert result == "message_id_456"
        mock_send.assert_called_once()
