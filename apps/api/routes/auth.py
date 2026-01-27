"""
Authentication Routes - Using SQLite Database
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from enum import Enum
import jwt
import bcrypt
import os
from datetime import datetime, timedelta
from typing import Optional
import uuid

from database import get_db
from models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()

# Settings
SECRET_KEY = os.getenv("JWT_SECRET", "routine-studio-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24 * 7  # 7 days


# Role Enum
class Role(str, Enum):
    ADMIN = "ADMIN"      # All permissions
    MANAGER = "MANAGER"  # Edit permissions
    VIEWER = "VIEWER"    # View only


# Pydantic models
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=15, description="Username (3-15 chars)")
    password: str = Field(..., min_length=3, max_length=15, description="Password (3-15 chars)")
    name: Optional[str] = None


class UserLogin(BaseModel):
    username: str = Field(..., min_length=3, max_length=15)
    password: str = Field(..., min_length=3, max_length=15)


class UserResponse(BaseModel):
    id: str
    username: str
    name: Optional[str]
    role: Role
    is_approved: bool
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# Helper functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_token(user_id: str, username: str, role: Role) -> str:
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": user_id,
        "username": username,
        "role": role.value,
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def user_to_response(user: User) -> UserResponse:
    """Convert User model to UserResponse"""
    return UserResponse(
        id=user.id,
        username=user.username,
        name=user.name,
        role=Role(user.role or "VIEWER"),
        is_approved=user.is_approved or False,
        created_at=user.created_at.isoformat() if user.created_at else datetime.utcnow().isoformat()
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    payload = verify_token(credentials.credentials)
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_approved:
        raise HTTPException(status_code=403, detail="Account not approved")
    return user


def require_role(*allowed_roles: Role):
    """Role-based access control dependency"""
    async def role_checker(user: User = Depends(get_current_user)):
        user_role = Role(user.role or "VIEWER")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Required role: {[r.value for r in allowed_roles]}"
            )
        return user
    return role_checker


# Routes
@router.post("/register", response_model=TokenResponse)
async def register(data: UserRegister, db: Session = Depends(get_db)):
    # Check for duplicate username
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="이미 사용 중인 아이디입니다")

    # Create user (pending approval)
    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        username=data.username,
        password_hash=hash_password(data.password),
        name=data.name or data.username,
        role=Role.VIEWER.value,
        is_approved=False,
        created_at=datetime.utcnow()
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Create token (but login won't work until approved)
    token = create_token(user_id, data.username, Role.VIEWER)

    return TokenResponse(
        access_token=token,
        user=user_to_response(user)
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: Session = Depends(get_db)):
    # Find user
    user = db.query(User).filter(User.username == data.username).first()

    if not user:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 일치하지 않습니다")

    # Check password
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 일치하지 않습니다")

    # Check approval status
    if not user.is_approved:
        raise HTTPException(status_code=403, detail="관리자 승인 대기 중입니다. 승인 후 로그인할 수 있습니다.")

    # Create token
    role = Role(user.role or "VIEWER")
    token = create_token(user.id, user.username, role)

    return TokenResponse(
        access_token=token,
        user=user_to_response(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user_to_response(user)


@router.post("/logout")
async def logout():
    return {"success": True, "message": "Logged out"}
