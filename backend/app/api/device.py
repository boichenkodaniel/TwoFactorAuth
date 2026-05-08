from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.models.user import User
from app.services.auth_service import verify_password
from app.storage.redis_client import redis_client

router = APIRouter(prefix="/device", tags=["Devices"])


class DeviceRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    fcm_token: str


class DeviceRegisterResponse(BaseModel):
    user_id: str
    message: str


class DeviceUnregisterRequest(BaseModel):
    user_id: str


class DeviceActionResponse(BaseModel):
    message: str


class DeviceListResponse(BaseModel):
    devices: list[dict]


@router.post("/register", response_model=DeviceRegisterResponse)
async def register_device(request: DeviceRegisterRequest):
    user = User.get_user_by_email(request.email)

    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    device_key = f"device:{user.id}"
    device_data = {
        "user_id": user.id,
        "email": user.email,
        "fcm_token": request.fcm_token,
    }

    redis_client.set_json(device_key, device_data)

    return DeviceRegisterResponse(
        user_id=user.id,
        message="Device registered successfully",
    )


@router.post("/unregister", response_model=DeviceActionResponse)
async def unregister_device(request: DeviceUnregisterRequest):
    user = User.get_user_by_id(request.user_id)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    redis_client.delete(f"device:{request.user_id}")

    return DeviceActionResponse(message="Device unregistered successfully")


@router.get("/list", response_model=DeviceListResponse)
async def list_devices():
    devices = []
    redis_client_instance = redis_client.get_redis()

    for key in redis_client_instance.scan_iter("device:*"):
        device_data = redis_client.get_json(key)
        if device_data:
            devices.append(device_data)

    return DeviceListResponse(devices=devices)
