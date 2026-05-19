import logging

from app.services.firebase import FirebaseService

logger = logging.getLogger(__name__)


class PushService:
    @classmethod
    def send_push_notification(
        cls,
        token: str,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> bool:
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
