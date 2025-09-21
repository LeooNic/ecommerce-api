"""
Test cases for authentication functionality.
"""

import pytest
from fastapi import status

from app.models.user import User, UserRole
from app.utils.auth import verify_password, get_password_hash, verify_token


class TestUserRegistration:
    """Test user registration functionality."""

    def test_register_user_success(self, client, test_user_data):
        """Test successful user registration."""
        response = client.post("/api/v1/auth/register", json=test_user_data)

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert "user" in data
        assert "token" in data
        assert "message" in data

        user_data = data["user"]
        assert user_data["email"] == test_user_data["email"]
        assert user_data["username"] == test_user_data["username"]
        assert user_data["first_name"] == test_user_data["first_name"]
        assert user_data["last_name"] == test_user_data["last_name"]
        assert user_data["role"] == test_user_data["role"]
        assert user_data["is_active"] is True
        assert user_data["is_verified"] is False

        token_data = data["token"]
        assert token_data["access_token"]
        assert token_data["token_type"] == "bearer"
        assert token_data["expires_in"] > 0

    def test_register_user_duplicate_email(self, client, test_user_data, created_user):
        """Test registration with duplicate email."""
        response = client.post("/api/v1/auth/register", json=test_user_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Email already registered" in response.json()["detail"]

    def test_register_user_duplicate_username(self, client, test_user_data, created_user):
        """Test registration with duplicate username."""
        different_email_data = test_user_data.copy()
        different_email_data["email"] = "different@example.com"

        response = client.post("/api/v1/auth/register", json=different_email_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Username already taken" in response.json()["detail"]

    def test_register_user_invalid_email(self, client, test_user_data):
        """Test registration with invalid email format."""
        invalid_data = test_user_data.copy()
        invalid_data["email"] = "invalid-email"

        response = client.post("/api/v1/auth/register", json=invalid_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_user_short_password(self, client, test_user_data):
        """Test registration with short password."""
        invalid_data = test_user_data.copy()
        invalid_data["password"] = "short"

        response = client.post("/api/v1/auth/register", json=invalid_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_admin_user(self, client, test_admin_data):
        """Test registration of admin user."""
        response = client.post("/api/v1/auth/register", json=test_admin_data)

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        user_data = data["user"]
        assert user_data["role"] == "admin"


class TestUserLogin:
    """Test user login functionality."""

    def test_login_success(self, client, created_user, test_user_data):
        """Test successful login."""
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        }

        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "user" in data
        assert "token" in data
        assert "message" in data

        user_data = data["user"]
        assert user_data["email"] == test_user_data["email"]

        token_data = data["token"]
        assert token_data["access_token"]
        assert token_data["token_type"] == "bearer"

    def test_login_wrong_email(self, client, created_user):
        """Test login with wrong email."""
        login_data = {
            "email": "wrong@example.com",
            "password": "testpassword123"
        }

        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Incorrect email or password" in response.json()["detail"]

    def test_login_wrong_password(self, client, created_user, test_user_data):
        """Test login with wrong password."""
        login_data = {
            "email": test_user_data["email"],
            "password": "wrongpassword"
        }

        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Incorrect email or password" in response.json()["detail"]

    def test_login_inactive_user(self, client, db_session, test_user_data):
        """Test login with inactive user."""
        # Create inactive user
        user = User(
            email=test_user_data["email"],
            username=test_user_data["username"],
            first_name=test_user_data["first_name"],
            last_name=test_user_data["last_name"],
            hashed_password=get_password_hash(test_user_data["password"]),
            role=test_user_data["role"],
            is_active=False
        )

        db_session.add(user)
        db_session.commit()

        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        }

        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Inactive user account" in response.json()["detail"]


class TestCurrentUser:
    """Test current user functionality."""

    def test_get_current_user_success(self, client, auth_headers, test_user_data):
        """Test getting current user information."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["username"] == test_user_data["username"]

    def test_get_current_user_without_token(self, client):
        """Test getting current user without authentication."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestTokenRefresh:
    """Test token refresh functionality."""

    def test_refresh_token_success(self, client, auth_headers):
        """Test successful token refresh."""
        response = client.post("/api/v1/auth/refresh", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    def test_refresh_token_without_auth(self, client):
        """Test token refresh without authentication."""
        response = client.post("/api/v1/auth/refresh")

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestPasswordUtilities:
    """Test password utility functions."""

    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False

    def test_token_verification(self):
        """Test JWT token verification."""
        from app.utils.auth import create_access_token

        # Create test token
        test_data = {"sub": "123", "email": "test@example.com", "role": "customer"}
        token = create_access_token(data=test_data)

        # Verify token
        token_data = verify_token(token)

        assert token_data is not None
        assert token_data.user_id == 123
        assert token_data.email == "test@example.com"
        assert token_data.role == "customer"

    def test_invalid_token_verification(self):
        """Test verification of invalid token."""
        invalid_token = "invalid.token.here"
        token_data = verify_token(invalid_token)

        assert token_data is None


class TestUserModel:
    """Test User model functionality."""

    def test_user_creation(self, db_session, test_user_data):
        """Test user model creation."""
        user = User(
            email=test_user_data["email"],
            username=test_user_data["username"],
            first_name=test_user_data["first_name"],
            last_name=test_user_data["last_name"],
            hashed_password=get_password_hash(test_user_data["password"]),
            role=test_user_data["role"]
        )

        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.id is not None
        assert user.email == test_user_data["email"]
        assert user.is_active is True
        assert user.is_verified is False

    def test_user_full_name_property(self, created_user):
        """Test user full name property."""
        assert created_user.full_name == "Test User"

    def test_user_is_admin_method(self, created_admin):
        """Test user is_admin method."""
        assert created_admin.is_admin() is True

    def test_user_is_not_admin(self, created_user):
        """Test user is_admin method for non-admin."""
        assert created_user.is_admin() is False

    def test_user_repr(self, created_user):
        """Test user string representation."""
        repr_str = repr(created_user)
        assert "User(" in repr_str
        assert f"id={created_user.id}" in repr_str
        assert f"email={created_user.email}" in repr_str