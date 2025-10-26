"""
Authentication API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.postgres import get_db
from backend.app.models.user import User
from backend.app.schemas.auth import TokenResponse, UserLogin, UserRegister, UserResponse
from backend.app.services.auth import get_current_user
from backend.app.services.security import (
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user

    Args:
        user_data: User registration data
        db: Database session

    Returns:
        User information

    Raises:
        HTTPException: If user already exists
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create new user
    hashed_password = hash_password(user_data.password)
    new_user = User(
        email=user_data.email,
        name=user_data.name,
        password_hash=hashed_password,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        name=new_user.name,
        created_at=new_user.created_at.isoformat(),
    )


@router.post("/token", response_model=TokenResponse)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    Login and get access token

    Args:
        user_data: User login credentials
        db: Database session

    Returns:
        Access token and user information

    Raises:
        HTTPException: If credentials are invalid
    """
    # Find user by email
    user = db.query(User).filter(User.email == user_data.email).first()

    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate access token
    access_token = create_access_token(user_id=user.id)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            created_at=user.created_at.isoformat(),
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Get current user information

    Args:
        current_user: Current authenticated user (from dependency)

    Returns:
        User information

    Raises:
        HTTPException: If not authenticated
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        created_at=current_user.created_at.isoformat(),
    )
