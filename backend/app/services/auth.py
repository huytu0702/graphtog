"""
Authentication service with dependency functions
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import logging

from app.db.postgres import get_db
from app.models.user import User
from app.schemas.auth import UserResponse, TokenPayload
from app.services.security import verify_token

logger = logging.getLogger(__name__)
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Get current user information

    Args:
        credentials: HTTP Bearer token credentials
        db: Database session

    Returns:
        Current user information

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    logger.info(f"🔐 Token received: {token[:20]}...")  # Log first 20 chars

    token_data = verify_token(token)
    if not token_data:
        logger.error(f"❌ Token verification failed for: {token[:20]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    logger.info(f"✅ Token verified for user: {token_data.sub}")
    user = db.query(User).filter(User.id == token_data.sub).first()
    if not user:
        logger.error(f"❌ User not found for ID: {token_data.sub}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    logger.info(f"✅ User authenticated: {user.email}")
    return user
