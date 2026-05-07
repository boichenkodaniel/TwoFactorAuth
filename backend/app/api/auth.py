from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.models.user import User
from app.services.auth_service import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterResponse(BaseModel):
    user_id: str
    message: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    status: str
    user_id: str | None = None


@router.post("/register", response_model=RegisterResponse)
async def register(request: RegisterRequest):
    password_hash = hash_password(request.password)

    user = User.create_user(email=request.email, password_hash=password_hash)

    if user is None:
        raise HTTPException(status_code=400, detail="Email already registered")

    return RegisterResponse(user_id=user.id, message="User registered successfully")


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    user = User.get_user_by_email(request.email)

    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return LoginResponse(status="2fa_required", user_id=user.id)
