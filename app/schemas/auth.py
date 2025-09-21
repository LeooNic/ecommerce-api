"""
Authentication Pydantic schemas for JWT and token handling.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.user import UserRole


class Token(BaseModel):
    """
    Schema for JWT token response.
    """

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class TokenData(BaseModel):
    """
    Schema for JWT token payload data.
    """

    user_id: Optional[int] = Field(None, description="User's unique identifier")
    email: Optional[str] = Field(None, description="User's email address")
    role: Optional[UserRole] = Field(None, description="User role")


class AuthResponse(BaseModel):
    """
    Schema for authentication response with user data and token.
    """

    user: dict = Field(..., description="User information")
    token: Token = Field(..., description="JWT token information")
    message: str = Field(..., description="Authentication success message")


class PasswordChange(BaseModel):
    """
    Schema for password change requests.
    """

    current_password: str = Field(..., min_length=1, description="Current password")
    new_password: str = Field(
        ..., min_length=8, max_length=100, description="New password"
    )


class PasswordReset(BaseModel):
    """
    Schema for password reset requests.
    """

    email: str = Field(..., description="User's email address for password reset")


class PasswordResetConfirm(BaseModel):
    """
    Schema for password reset confirmation.
    """

    token: str = Field(..., description="Password reset token")
    new_password: str = Field(
        ..., min_length=8, max_length=100, description="New password"
    )
