from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from ..models.user import User, UserRole
from .config import settings
from .database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# tokenUrl is used only by Swagger UI's Authorize button — does not affect token extraction.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------

def create_access_token(subject: Any) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(subject), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: Any, version: int = 0) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(subject), "exp": expire, "type": "refresh", "ver": version}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ---------------------------------------------------------------------------
# Token decoding
# ---------------------------------------------------------------------------

def _decode_raw(token: str) -> dict:
    """Decode and verify signature; raises JWTError on failure."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def decode_access_token(token: str) -> dict:
    """Decode an access token; raises HTTPException if invalid or wrong type."""
    try:
        payload = _decode_raw(token)
    except JWTError:
        raise _CREDENTIALS_EXC
    if payload.get("type") != "access":
        raise _CREDENTIALS_EXC
    return payload


def decode_refresh_token(token: str) -> dict:
    """Decode a refresh token; raises HTTPException if invalid or wrong type."""
    try:
        payload = _decode_raw(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is not a refresh token",
        )
    return payload


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise _CREDENTIALS_EXC

    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXC
    return user


def create_password_reset_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    payload = {"sub": str(user_id), "exp": expire, "type": "password_reset"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_password_reset_token(token: str) -> dict:
    try:
        payload = _decode_raw(token)
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    if payload.get("type") != "password_reset":
        raise HTTPException(status_code=400, detail="Invalid token type")
    return payload


def require_role(*roles: UserRole) -> Callable:
    """Return a dependency that enforces role membership.

    Usage::

        @router.get("/admin-only")
        def admin_view(_: User = Depends(require_role(UserRole.admin))):
            ...
    """
    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access restricted to: {', '.join(r.value for r in roles)}",
            )
        return current_user

    return _checker
