import pytest
from unittest.mock import MagicMock, patch
from app.services.push_service import PushService


def test_send_push_notification_success():
    with patch("app.services.push_service.FirebaseService.send_message") as mock_send:
        mock_send.return_value = "message_id"

        result = PushService.send_push_notification(
            token="test_token",
            title="Test Title",
            body="Test Body",
            data={"type": "login_request", "request_id": "123"},
        )

        assert result is True
        mock_send.assert_called_once()


def test_send_push_notification_without_data():
    with patch("app.services.push_service.FirebaseService.send_message") as mock_send:
        mock_send.return_value = "message_id"

        result = PushService.send_push_notification(
            token="test_token",
            title="Test Title",
            body="Test Body",
        )

        assert result is True


def test_send_push_notification_failure():
    with patch("app.services.push_service.FirebaseService.send_message") as mock_send:
        mock_send.side_effect = Exception("Firebase error")

        result = PushService.send_push_notification(
            token="test_token",
            title="Test Title",
            body="Test Body",
        )

        assert result is False
