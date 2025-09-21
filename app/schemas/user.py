"""
User Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class UserBase(BaseModel):
    """
    Base user schema with common fields.
    """

    email: EmailStr = Field(..., description="User's email address")
    username: str = Field(
        ..., min_length=3, max_length=50, description="Unique username"
    )
    first_name: str = Field(
        ..., min_length=1, max_length=100, description="User's first name"
    )
    last_name: str = Field(
        ..., min_length=1, max_length=100, description="User's last name"
    )


class UserCreate(UserBase):
    """
    Schema for user creation requests.
    """

    password: str = Field(
        ..., min_length=8, max_length=100, description="User's password"
    )
    role: Optional[UserRole] = Field(default=UserRole.CUSTOMER, description="User role")


class UserUpdate(BaseModel):
    """
    Schema for user update requests.
    """

    email: Optional[EmailStr] = Field(None, description="User's email address")
    username: Optional[str] = Field(
        None, min_length=3, max_length=50, description="Unique username"
    )
    first_name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="User's first name"
    )
    last_name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="User's last name"
    )
    is_active: Optional[bool] = Field(None, description="User active status")
    is_verified: Optional[bool] = Field(None, description="User verification status")


class UserResponse(UserBase):
    """
    Schema for user response data.
    """

    id: int = Field(..., description="User's unique identifier")
    role: UserRole = Field(..., description="User role")
    is_active: bool = Field(..., description="User active status")
    is_verified: bool = Field(..., description="User verification status")
    created_at: datetime = Field(..., description="User creation timestamp")
    updated_at: datetime = Field(..., description="User last update timestamp")

    model_config = {"from_attributes": True}


class UserLogin(BaseModel):
    """
    Schema for user login requests.
    """

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=1, description="User's password")
