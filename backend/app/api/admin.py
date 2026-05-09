from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.models.user import User
from app.security.admin_auth import require_admin
from app.storage.redis_client import redis_client

router = APIRouter(tags=["Admin"])

templates = Jinja2Templates(directory="app/templates")


@router.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, _: str = Depends(require_admin)):
    users = []
    devices = []
    login_requests = []
    devices_by_user_id = {}

    redis_client_instance = redis_client.get_redis()

    for key in redis_client_instance.scan_iter("user:*"):
        if not key.startswith("user:"):
            continue
        user_data = redis_client.get_json(key)
        if user_data:
            users.append(user_data)

    for key in redis_client_instance.scan_iter("device:*"):
        device_data = redis_client.get_json(key)
        if device_data:
            devices.append(device_data)
            user_id = device_data.get("user_id")
            if user_id:
                devices_by_user_id[user_id] = device_data

    for key in redis_client_instance.scan_iter("login_request:*"):
        request_data = redis_client.get_json(key)
        if request_data:
            login_requests.append(request_data)

    return templates.TemplateResponse(
        request,
        "admin.html",
        {
            "users": users,
            "devices": devices,
            "devices_by_user_id": devices_by_user_id,
            "login_requests": login_requests,
            "message": request.query_params.get("message", ""),
        },
    )


@router.post("/admin/devices/{user_id}/unregister")
async def admin_unregister_device(user_id: str, _: str = Depends(require_admin)):
    user = User.get_user_by_id(user_id)
    if user is None:
        return RedirectResponse(url="/admin?message=User+not+found", status_code=303)

    redis_client.delete(f"device:{user_id}")
    return RedirectResponse(url="/admin?message=Device+unregistered+successfully", status_code=303)
