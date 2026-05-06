"""
Slowapi rate-limiter for AI endpoints.

Key strategy: rate-limit per authenticated user (via JWT sub claim) so
users cannot bypass the limit by rotating IPs. Falls back to client IP
for unauthenticated requests.
"""
from fastapi import Request
from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import settings


def _get_user_key(request: Request) -> str:
    """Return 'user:<id>' for authenticated requests, otherwise client IP."""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                options={"verify_exp": False},   # just extract sub, not full validation
            )
            sub = payload.get("sub")
            if sub:
                return f"user:{sub}"
        except JWTError:
            pass
    return get_remote_address(request)


limiter = Limiter(key_func=_get_user_key, default_limits=[])
