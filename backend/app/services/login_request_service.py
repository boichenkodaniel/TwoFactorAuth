import uuid
from enum import Enum
from typing import Optional

from app.storage.redis_client import redis_client


class LoginRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class LoginRequest:
    def __init__(
        self,
        user_id: str,
        request_id: Optional[str] = None,
        status: LoginRequestStatus = LoginRequestStatus.PENDING,
        site_name: Optional[str] = None,
    ):
        self.request_id = request_id or str(uuid.uuid4())
        self.user_id = user_id
        self.status = status
        self.site_name = site_name or "Unknown site"

    @staticmethod
    def _request_key(request_id: str) -> str:
        return f"login_request:{request_id}"

    def save(self, ttl: int = 120) -> bool:
        data = {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "status": self.status.value,
            "site_name": self.site_name,
        }
        return redis_client.set_json(self._request_key(self.request_id), data, ex=ttl)

    @classmethod
    def create_request(cls, user_id: str, ttl: int = 120, site_name: Optional[str] = None) -> "LoginRequest":
        request = cls(user_id=user_id, site_name=site_name)
        request.save(ttl=ttl)
        return request

    @classmethod
    def get_request(cls, request_id: str) -> Optional["LoginRequest"]:
        data = redis_client.get_json(cls._request_key(request_id))
        if data is None:
            return None
        return cls(
            user_id=data["user_id"],
            request_id=data["request_id"],
            status=LoginRequestStatus(data["status"]),
            site_name=data.get("site_name"),
        )

    def approve(self, ttl: int = 120) -> bool:
        self.status = LoginRequestStatus.APPROVED
        return self.save(ttl=ttl)

    def deny(self, ttl: int = 120) -> bool:
        self.status = LoginRequestStatus.DENIED
        return self.save(ttl=ttl)

    def get_status(self) -> LoginRequestStatus:
        return self.status
