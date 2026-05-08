import logging

from app.services.firebase import FirebaseService

logger = logging.getLogger(__name__)


class PushService:
    """Service for sending push notifications."""

    @classmethod
    def send_push_notification(
        cls,
        token: str,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> bool:
        """Send push notification via FCM.

        Args:
            token: FCM device token.
            title: Notification title.
            body: Notification body.
            data: Optional data payload.

        Returns:
            True if sent successfully, False otherwise.
        """
        try:
            FirebaseService.send_message(
                token=token,
                title=title,
                body=body,
                data=data,
            )
            return True
        except Exception as exc:
            logger.exception("Failed to send push notification: %s", exc)
            return False
