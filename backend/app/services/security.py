"""
Security utilities for authentication
Handles JWT token generation/validation and password hashing
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.schemas.auth import TokenPayload

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Get settings
settings = get_settings()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: UUID, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token

    Args:
        user_id: UUID of the user
        expires_delta: Optional expiration time delta

    Returns:
        JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    return encoded_jwt


def verify_token(token: str) -> Optional[TokenPayload]:
    """
    Verify and decode a JWT token

    Args:
        token: JWT token string

    Returns:
        TokenPayload if valid, None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        token_data = TokenPayload(sub=user_id, exp=payload.get("exp"))
        return token_data
    except JWTError:
        return None
