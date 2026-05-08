from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import HTTPException, status
from app.core.config import get_settings

settings = get_settings()

_HASHED_USERS: dict = {}


def _get_hashed_users() -> dict:
    global _HASHED_USERS
    if not _HASHED_USERS:
        # Passwords loaded from env — never hardcoded
        admin_password   = settings.admin_password
        analyst_password = settings.analyst_password

        _HASHED_USERS = {
            "admin": {
                "username":        "admin",
                "hashed_password": bcrypt.hashpw(
                    admin_password.encode("utf-8"),
                    bcrypt.gensalt()
                ),
                "role": "admin",
            },
            "analyst": {
                "username":        "analyst",
                "hashed_password": bcrypt.hashpw(
                    analyst_password.encode("utf-8"),
                    bcrypt.gensalt()
                ),
                "role": "analyst",
            },
        }
    return _HASHED_USERS


def verify_password(plain: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed)


def authenticate_user(username: str, password: str) -> Optional[dict]:
    user = _get_hashed_users().get(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


def create_access_token(data: dict) -> str:
    payload = data.copy()
    expire  = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload.update({"exp": expire})
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )