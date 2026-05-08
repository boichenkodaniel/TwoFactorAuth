from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.models.user import User
from app.services.login_request_service import LoginRequest, LoginRequestStatus
from app.services.push_service import PushService
from app.storage.redis_client import redis_client

router = APIRouter(prefix="/2fa/push", tags=["Push Authentication"])


class PushRequest(BaseModel):
    user_id: str
    site_name: str | None = None


class PushRequestResponse(BaseModel):
    request_id: str
    status: str


class PushActionRequest(BaseModel):
    request_id: str


class PushActionResponse(BaseModel):
    status: str
    message: str


class PushStatusResponse(BaseModel):
    request_id: str
    status: str
    site_name: str | None = None


def resolve_site_name(request: Request, explicit_site_name: str | None) -> str:
    if explicit_site_name:
        return explicit_site_name

    referer = request.headers.get("referer")
    if referer:
        parsed = urlparse(referer)
        if parsed.netloc:
            return parsed.netloc

    origin = request.headers.get("origin")
    if origin:
        parsed = urlparse(origin)
        if parsed.netloc:
            return parsed.netloc

    host = request.headers.get("host")
    if host:
        return host

    return "Unknown site"


@router.post("/request", response_model=PushRequestResponse)
async def request_push(request: PushRequest, http_request: Request):
    user = User.get_user_by_id(request.user_id)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    site_name = resolve_site_name(http_request, request.site_name)
    login_request = LoginRequest.create_request(user_id=request.user_id, site_name=site_name)

    device_data = redis_client.get_json(f"device:{request.user_id}")
    if device_data:
        fcm_token = device_data.get("fcm_token")
        if fcm_token:
            PushService.send_push_notification(
                token=fcm_token,
                title="Login Attempt",
                body=f"Sign-in request from {site_name}",
                data={
                    "type": "login_request",
                    "request_id": login_request.request_id,
                    "site_name": site_name,
                    "title": "Login request detected",
                    "body": f"Sign-in request from {site_name}",
                },
            )

    return PushRequestResponse(request_id=login_request.request_id, status="pending")


@router.get("/status/{request_id}", response_model=PushStatusResponse)
async def get_push_status(request_id: str):
    """Check the status of a push authentication request"""
    login_request = LoginRequest.get_request(request_id)

    if login_request is None:
        raise HTTPException(status_code=404, detail="Login request not found")

    return PushStatusResponse(
        request_id=request_id,
        status=login_request.get_status().value,
        site_name=login_request.site_name,
    )


@router.get("/pending/{user_id}", response_model=PushStatusResponse)
async def get_pending_push_request(user_id: str):
    redis_client_instance = redis_client.get_redis()

    for key in redis_client_instance.scan_iter("login_request:*"):
        request_data = redis_client.get_json(key)
        if not request_data:
            continue
        if request_data.get("user_id") != user_id:
            continue
        if request_data.get("status") != LoginRequestStatus.PENDING.value:
            continue
        return PushStatusResponse(
            request_id=request_data["request_id"],
            status=request_data["status"],
            site_name=request_data.get("site_name"),
        )

    raise HTTPException(status_code=404, detail="No pending login request found")


@router.post("/approve", response_model=PushActionResponse)
async def approve_push(request: PushActionRequest):
    login_request = LoginRequest.get_request(request.request_id)

    if login_request is None:
        raise HTTPException(status_code=404, detail="Login request not found")

    login_request.approve()

    return PushActionResponse(status="approved", message="Login approved successfully")


@router.post("/deny", response_model=PushActionResponse)
async def deny_push(request: PushActionRequest):
    login_request = LoginRequest.get_request(request.request_id)

    if login_request is None:
        raise HTTPException(status_code=404, detail="Login request not found")

    login_request.deny()

    return PushActionResponse(status="denied", message="Login denied")
