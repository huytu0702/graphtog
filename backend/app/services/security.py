"""
Security utilities for authentication
Handles JWT token generation/validation and password hashing
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
import logging

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.schemas.auth import TokenPayload

logger = logging.getLogger(__name__)

# Password hashing context - use argon2 for better compatibility
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

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

    # Use UTC timestamp for consistency
    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    logger.info(f"🔐 Creating token for user {user_id}")
    logger.info(f"⏰ Current time (UTC): {now}")
    logger.info(f"⏰ Token will expire at (UTC): {expire}")
    logger.info(f"⏰ Token lifetime: {expires_delta.total_seconds() / 60} minutes")

    # Convert to Unix timestamps (seconds since epoch) for JWT
    to_encode = {
        "sub": str(user_id),
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
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
        # Decode without verification first to see the claims
        unverified_payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False},
        )

        exp_timestamp = unverified_payload.get("exp")
        iat_timestamp = unverified_payload.get("iat")
        now = datetime.now(timezone.utc).timestamp()

        logger.info(f"🔍 Token verification debug:")
        logger.info(f"   Current time (UTC): {datetime.fromtimestamp(now, tz=timezone.utc)}")
        logger.info(
            f"   Token issued at: {datetime.fromtimestamp(iat_timestamp, tz=timezone.utc) if iat_timestamp else 'N/A'}"
        )
        logger.info(
            f"   Token expires at: {datetime.fromtimestamp(exp_timestamp, tz=timezone.utc) if exp_timestamp else 'N/A'}"
        )
        logger.info(
            f"   Time until expiration: {(exp_timestamp - now) / 60:.2f} minutes"
            if exp_timestamp
            else "N/A"
        )

        # Now verify with expiration check
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            logger.warning("❌ Token does not contain 'sub' claim")
            return None
        token_data = TokenPayload(sub=user_id, exp=payload.get("exp"))
        logger.info(f"✅ Token verified successfully for user: {user_id}")
        return token_data
    except JWTError as e:
        logger.error(f"❌ JWT verification error: {str(e)}")
        return None
