"""
Test configuration and fixtures.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.models.product import Product
from app.models.category import Category
from app.utils.auth import get_password_hash


# Test database URL
TEST_DATABASE_URL = "sqlite:///./test_ecommerce.db"

# Create test engine
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Create test session maker
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """
    Create a fresh database session for each test.
    """
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create session
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    Create a test client with overridden database dependency.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """
    Test user data for registration.
    """
    return {
        "email": "test@example.com",
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "password": "testpassword123",
        "role": "customer"
    }


@pytest.fixture
def test_admin_data():
    """
    Test admin user data.
    """
    return {
        "email": "admin@example.com",
        "username": "admin",
        "first_name": "Admin",
        "last_name": "User",
        "password": "adminpassword123",
        "role": "admin"
    }


@pytest.fixture
def created_user(db_session, test_user_data):
    """
    Create a test user in the database.
    """
    user = User(
        email=test_user_data["email"],
        username=test_user_data["username"],
        first_name=test_user_data["first_name"],
        last_name=test_user_data["last_name"],
        hashed_password=get_password_hash(test_user_data["password"]),
        role=test_user_data["role"],
        is_active=True,
        is_verified=False
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


@pytest.fixture
def created_admin(db_session, test_admin_data):
    """
    Create a test admin user in the database.
    """
    admin = User(
        email=test_admin_data["email"],
        username=test_admin_data["username"],
        first_name=test_admin_data["first_name"],
        last_name=test_admin_data["last_name"],
        hashed_password=get_password_hash(test_admin_data["password"]),
        role=test_admin_data["role"],
        is_active=True,
        is_verified=True
    )

    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    return admin


@pytest.fixture
def auth_headers(client, created_user, test_user_data):
    """
    Get authentication headers for test user.
    """
    login_data = {
        "email": test_user_data["email"],
        "password": test_user_data["password"]
    }

    response = client.post("/api/v1/auth/login", json=login_data)
    token = response.json()["token"]["access_token"]

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(client, created_admin, test_admin_data):
    """
    Get authentication headers for test admin.
    """
    login_data = {
        "email": test_admin_data["email"],
        "password": test_admin_data["password"]
    }

    response = client.post("/api/v1/auth/login", json=login_data)
    token = response.json()["token"]["access_token"]

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_category(db_session):
    """
    Create a test category in the database.
    """
    from decimal import Decimal

    category = Category(
        name="Test Category",
        description="A test category for testing",
        slug="test-category",
        is_active=True
    )

    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    return category


@pytest.fixture
def test_product(db_session, test_category):
    """
    Create a test product in the database.
    """
    from decimal import Decimal

    product = Product(
        name="Test Product",
        description="A test product for testing",
        slug="test-product",
        sku="TEST-001",
        price=Decimal("29.99"),
        compare_price=Decimal("39.99"),
        cost_price=Decimal("19.99"),
        stock_quantity=100,
        low_stock_threshold=10,
        weight=Decimal("1.5"),
        dimensions="10x5x2 cm",
        category_id=test_category.id,
        is_active=True,
        is_featured=False,
        requires_shipping=True,
        meta_title="Test Product - Buy Now",
        meta_description="Test product for testing purposes"
    )

    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    return product


@pytest.fixture
def test_user_token(client, created_user, test_user_data):
    """
    Get authentication token for test user.
    """
    login_data = {
        "email": test_user_data["email"],
        "password": test_user_data["password"]
    }

    response = client.post("/api/v1/auth/login", json=login_data)
    return response.json()["token"]["access_token"]


@pytest.fixture
def test_admin_token(client, created_admin, test_admin_data):
    """
    Get authentication token for test admin.
    """
    login_data = {
        "email": test_admin_data["email"],
        "password": test_admin_data["password"]
    }

    response = client.post("/api/v1/auth/login", json=login_data)
    return response.json()["token"]["access_token"]