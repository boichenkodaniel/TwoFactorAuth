import uuid
from typing import Optional
from pydantic import BaseModel

from app.storage.redis_client import redis_client


class User(BaseModel):
    id: str
    email: str
    password_hash: str
    totp_secret: Optional[str] = None

    @staticmethod
    def _user_key(user_id: str) -> str:
        return f"user:{user_id}"

    @staticmethod
    def _email_index_key(email: str) -> str:
        return f"email_index:{email}"

    @classmethod
    def create_user(cls, email: str, password_hash: str, totp_secret: Optional[str] = None) -> Optional["User"]:
        if cls.get_user_by_email(email) is not None:
            return None

        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            email=email,
            password_hash=password_hash,
            totp_secret=totp_secret,
        )

        redis_client.set_json(cls._user_key(user_id), user.model_dump())
        redis_client.set_json(cls._email_index_key(email), user_id)

        return user

    @classmethod
    def get_user_by_email(cls, email: str) -> Optional["User"]:
        user_id = redis_client.get_json(cls._email_index_key(email))
        if user_id is None:
            return None
        return cls.get_user_by_id(user_id)

    @classmethod
    def get_user_by_id(cls, user_id: str) -> Optional["User"]:
        data = redis_client.get_json(cls._user_key(user_id))
        if data is None:
            return None
        return User(**data)

    @classmethod
    def update_user(cls, user: "User") -> bool:
        return redis_client.set_json(cls._user_key(user.id), user.model_dump())
