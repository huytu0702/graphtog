"""
Pydantic schemas for authentication endpoints
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema"""

    email: EmailStr
    name: Optional[str] = None


class UserRegister(UserBase):
    """Schema for user registration"""

    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")


class UserLogin(BaseModel):
    """Schema for user login"""

    email: EmailStr
    password: str


class UserResponse(UserBase):
    """Schema for user response"""

    id: UUID
    created_at: str

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for token response"""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenPayload(BaseModel):
    """Schema for JWT token payload"""

    sub: str  # user_id
    exp: int
