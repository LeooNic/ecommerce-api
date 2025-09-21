"""
Authentication routes for user registration and login.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.email_service import email_service
from app.logging_config import get_logger
from app.models.user import User
from app.rate_limiting import RateLimitConfig, limiter
from app.schemas.auth import AuthResponse, Token
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.utils.auth import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    get_password_hash,
)

logger = get_logger(__name__)


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email and password. Automatically sends welcome email.",
    response_description="User data with JWT access token for immediate authentication",
    responses={
        201: {
            "description": "User successfully registered",
            "content": {
                "application/json": {
                    "example": {
                        "user": {
                            "id": 1,
                            "email": "user@example.com",
                            "username": "newuser",
                            "first_name": "John",
                            "last_name": "Doe",
                            "role": "customer",
                            "is_active": True,
                            "created_at": "2024-01-01T12:00:00.000Z",
                        },
                        "token": {
                            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                            "token_type": "bearer",
                            "expires_in": 1800,
                        },
                        "message": "User registered successfully",
                    }
                }
            },
        },
        400: {
            "description": "Email or username already exists",
            "content": {
                "application/json": {"example": {"detail": "Email already registered"}}
            },
        },
    },
)
@limiter.limit(RateLimitConfig.AUTH_LIMIT)
async def register_user(
    request: Request, user_data: UserCreate, db: Session = Depends(get_db)
) -> AuthResponse:
    """
    Register a new user account.

    Creates a new user with the provided information and returns an authentication token.
    The user will receive a welcome email notification after successful registration.

    - **email**: Must be unique and valid email format
    - **username**: Must be unique, 3-50 characters
    - **password**: Minimum 8 characters with complexity requirements
    - **first_name**: User's first name
    - **last_name**: User's last name
    - **role**: Either 'customer' or 'admin' (defaults to 'customer')
    """
    # Verificar si el email ya existe
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Verificar si el username ya existe
    existing_username = (
        db.query(User).filter(User.username == user_data.username).first()
    )
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
        )

    try:
        # Crear nuevo usuario
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            email=user_data.email,
            username=user_data.username,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            hashed_password=hashed_password,
            role=user_data.role,
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        # Crear token de acceso
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": str(db_user.id), "email": db_user.email, "role": db_user.role},
            expires_delta=access_token_expires,
        )

        # Preparar respuesta
        token = Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )

        user_response = UserResponse.model_validate(db_user)

        # Send welcome email notification
        try:
            await email_service.send_welcome_email(
                user_email=db_user.email,
                user_name=f"{db_user.first_name} {db_user.last_name}",
            )
            logger.info(f"Welcome email sent to {db_user.email}")
        except Exception as e:
            logger.error(f"Failed to send welcome email to {db_user.email}: {e}")

        return AuthResponse(
            user=user_response.model_dump(),
            token=token,
            message="User registered successfully",
        )

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists",
        )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="User login",
    description="Authenticate user with email and password to receive access token",
    response_description="User data with JWT access token",
    responses={
        200: {
            "description": "Login successful",
            "content": {
                "application/json": {
                    "example": {
                        "user": {
                            "id": 1,
                            "email": "user@example.com",
                            "username": "existinguser",
                            "first_name": "John",
                            "last_name": "Doe",
                            "role": "customer",
                            "is_active": True,
                            "created_at": "2024-01-01T12:00:00.000Z",
                        },
                        "token": {
                            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                            "token_type": "bearer",
                            "expires_in": 1800,
                        },
                        "message": "Login successful",
                    }
                }
            },
        },
        401: {
            "description": "Invalid credentials",
            "content": {
                "application/json": {
                    "example": {"detail": "Incorrect email or password"}
                }
            },
        },
        400: {
            "description": "Inactive user account",
            "content": {
                "application/json": {"example": {"detail": "Inactive user account"}}
            },
        },
    },
)
@limiter.limit(RateLimitConfig.AUTH_LIMIT)
async def login_user(
    request: Request, login_data: UserLogin, db: Session = Depends(get_db)
) -> AuthResponse:
    """
    Authenticate user and generate access token.

    Validates user credentials and returns JWT token for API access.
    Token expires in 30 minutes by default.

    - **email**: User's registered email address
    - **password**: User's password
    """
    # Autenticar usuario
    user = authenticate_user(db, login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verificar si el usuario está activo
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user account"
        )

    # Crear token de acceso
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role},
        expires_delta=access_token_expires,
    )

    # Preparar respuesta
    token = Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )

    user_response = UserResponse.model_validate(user)

    return AuthResponse(
        user=user_response.model_dump(), token=token, message="Login successful"
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user information",
    description="Retrieve the authenticated user's profile information",
    response_description="Current user's profile data",
    responses={
        200: {
            "description": "User information retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "email": "user@example.com",
                        "username": "currentuser",
                        "first_name": "John",
                        "last_name": "Doe",
                        "role": "customer",
                        "is_active": True,
                        "created_at": "2024-01-01T12:00:00.000Z",
                    }
                }
            },
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {"example": {"detail": "Not authenticated"}}
            },
        },
    },
)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """
    Get current authenticated user's profile information.

    Returns detailed information about the currently authenticated user.
    Requires valid JWT token in Authorization header.
    """
    return UserResponse.model_validate(current_user)


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token",
    description="Generate a new JWT access token for the authenticated user",
    response_description="New JWT access token",
    responses={
        200: {
            "description": "Token refreshed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "token_type": "bearer",
                        "expires_in": 1800,
                    }
                }
            },
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {"example": {"detail": "Not authenticated"}}
            },
        },
    },
)
async def refresh_token(current_user: User = Depends(get_current_active_user)) -> Token:
    """
    Generate a new JWT access token.

    Creates a fresh access token for the authenticated user with updated expiration time.
    Useful for extending session without requiring re-authentication.
    """
    # Crear nuevo token de acceso
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub": str(current_user.id),
            "email": current_user.email,
            "role": current_user.role,
        },
        expires_delta=access_token_expires,
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )
