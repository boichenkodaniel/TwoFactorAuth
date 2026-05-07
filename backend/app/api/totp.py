import base64
import io

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.models.user import User
from app.services.totp_service import TOTPService

router = APIRouter(prefix="/2fa/totp", tags=["TOTP"])


class TOTPSetupResponse(BaseModel):
    secret: str
    uri: str
    qr_code_data_url: str
    account_name: str


class TOTPVerifyRequest(BaseModel):
    user_id: str
    code: str


class TOTPVerifyResponse(BaseModel):
    valid: bool
    message: str


def generate_qr_code_data_url(uri: str) -> str:
    import qrcode

    qr = qrcode.make(uri)
    buffered = io.BytesIO()
    qr.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{qr_base64}"


@router.post("/setup", response_model=TOTPSetupResponse)
async def setup_totp(user_id: str, email: str = None):
    user = User.get_user_by_id(user_id)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    secret = TOTPService.generate_secret()
    user.totp_secret = secret
    User.update_user(user)

    account_name = email or user.email or user.id
    uri = TOTPService.build_provisioning_uri(secret, account_name)

    return TOTPSetupResponse(
        secret=secret,
        uri=uri,
        qr_code_data_url=generate_qr_code_data_url(uri),
        account_name=account_name,
    )


@router.get("/setup/{user_id}", response_class=HTMLResponse)
async def setup_totp_qr(user_id: str):
    user = User.get_user_by_id(user_id)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.totp_secret:
        user.totp_secret = TOTPService.generate_secret()
        User.update_user(user)

    account_name = user.email or user.id
    uri = TOTPService.build_provisioning_uri(user.totp_secret, account_name)
    qr_code_data_url = generate_qr_code_data_url(uri)

    return f"""
    <html>
    <head>
        <title>TOTP Setup</title>
        <style>
            body {{ font-family: Arial; text-align: center; padding: 50px; }}
            .qr {{ margin: 20px auto; }}
            .secret {{ background: #f0f0f0; padding: 10px; margin: 20px; display: inline-block; }}
        </style>
    </head>
    <body>
        <h1>2FA Setup</h1>
        <p>Scan this QR code with Authy or any TOTP authenticator</p>
        <div class="qr">
            <img src="{qr_code_data_url}" alt="QR Code" />
        </div>
        <div class="secret">
            <p><strong>Secret:</strong> {user.totp_secret}</p>
            <p><strong>Account:</strong> {account_name}</p>
            <p>Or enter manually if you can't scan</p>
        </div>
        <p>After setup, use the 6-digit code to verify</p>
    </body>
    </html>
    """


@router.post("/verify", response_model=TOTPVerifyResponse)
async def verify_totp(request: TOTPVerifyRequest):
    user = User.get_user_by_id(request.user_id)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user.totp_secret is None:
        raise HTTPException(status_code=400, detail="TOTP not configured")

    is_valid = TOTPService.verify_totp(user.totp_secret, request.code)

    if is_valid:
        return TOTPVerifyResponse(valid=True, message="TOTP verified successfully")

    raise HTTPException(status_code=401, detail="Invalid TOTP code")
