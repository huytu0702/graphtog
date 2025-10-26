"""
Authentication service with dependency functions
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.app.db.postgres import get_db
from backend.app.models.user import User
from backend.app.schemas.auth import UserResponse, TokenPayload
from backend.app.services.security import verify_token


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

    token_data = verify_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user = db.query(User).filter(User.id == token_data.sub).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user