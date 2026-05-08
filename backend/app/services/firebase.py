"""Firebase Admin SDK initialization module.

This module handles Firebase initialization for push notifications.
It supports loading credentials from environment variables, a local
`serviceAccountKey.json`, or default credentials.
"""

import json
import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, messaging


class FirebaseService:
    """Service for Firebase Cloud Messaging operations."""

    _initialized = False

    @classmethod
    def initialize(cls) -> None:
        """Initialize Firebase Admin SDK if not already initialized."""
        if cls._initialized:
            return

        firebase_config = os.getenv("FIREBASE_CREDENTIALS")
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        if not credentials_path:
            project_root = Path(__file__).resolve().parents[2]
            local_service_account = project_root / "serviceAccountKey.json"
            if local_service_account.exists():
                credentials_path = str(local_service_account)

        if firebase_config:
            cred_dict = json.loads(firebase_config)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
        elif credentials_path:
            cred = credentials.Certificate(credentials_path)
            firebase_admin.initialize_app(cred)
        else:
            firebase_admin.initialize_app()

        cls._initialized = True

    @classmethod
    def send_message(
        cls,
        token: str,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> str:
        """Send a push notification via FCM.

        Args:
            token: FCM device token.
            title: Notification title.
            body: Notification body.
            data: Optional data payload.

        Returns:
            Message ID from FCM.
        """
        cls.initialize()

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            token=token,
        )

        return messaging.send(message)
