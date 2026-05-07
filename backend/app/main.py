from app.core.env import load_env_file

load_env_file()

from fastapi import Depends, FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request

from app.api.auth import router as auth_router
from app.api.totp import router as totp_router
from app.api.device import router as device_router
from app.api.push import router as push_router
from app.api.admin import router as admin_router
from app.security.admin_auth import require_admin

app = FastAPI(
    title="2FA Authentication Service",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.include_router(auth_router)
app.include_router(totp_router)
app.include_router(device_router)
app.include_router(push_router)
app.include_router(admin_router)

templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Main web interface for 2FA"""
    return templates.TemplateResponse(request, "index.html", {})


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/openapi.json", include_in_schema=False)
async def openapi_endpoint(_: str = Depends(require_admin)):
    return get_openapi(
        title=app.title,
        version="1.0.0",
        description="2FA Authentication Service API",
        routes=app.routes,
    )


@app.get("/docs", include_in_schema=False)
async def docs(_: str = Depends(require_admin)):
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{app.title} - Swagger UI",
    )


@app.get("/redoc", include_in_schema=False)
async def redoc(_: str = Depends(require_admin)):
    return get_redoc_html(
        openapi_url="/openapi.json",
        title=f"{app.title} - ReDoc",
    )
