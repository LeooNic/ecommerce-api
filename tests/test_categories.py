"""
Comprehensive tests for Categories functionality.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.category import Category
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.services.category import CategoryService


class TestCategoryService:
    """
    Test cases for CategoryService.
    """

    def test_create_category(self, db_session: Session):
        """Test creating a new category."""
        category_data = CategoryCreate(
            name="Electronics",
            description="Electronic devices and accessories",
            slug="electronics",
            is_active=True,
        )

        category = CategoryService.create_category(db_session, category_data)

        assert category.id is not None
        assert category.name == "Electronics"
        assert category.slug == "electronics"
        assert category.is_active is True
        assert category.created_at is not None
        assert category.updated_at is not None

    def test_create_duplicate_category_name(self, db_session: Session):
        """Test creating category with duplicate name."""
        category_data = CategoryCreate(
            name="Electronics",
            description="Electronic devices",
            slug="electronics",
            is_active=True,
        )

        # Create first category
        CategoryService.create_category(db_session, category_data)

        # Try to create duplicate
        duplicate_data = CategoryCreate(
            name="Electronics",
            description="Different description",
            slug="electronics-2",
            is_active=True,
        )

        with pytest.raises(Exception):
            CategoryService.create_category(db_session, duplicate_data)

    def test_create_duplicate_category_slug(self, db_session: Session):
        """Test creating category with duplicate slug."""
        category_data = CategoryCreate(
            name="Electronics",
            description="Electronic devices",
            slug="electronics",
            is_active=True,
        )

        # Create first category
        CategoryService.create_category(db_session, category_data)

        # Try to create duplicate slug
        duplicate_data = CategoryCreate(
            name="Electronics Store",
            description="Different description",
            slug="electronics",
            is_active=True,
        )

        with pytest.raises(Exception):
            CategoryService.create_category(db_session, duplicate_data)

    def test_get_category(self, db_session: Session):
        """Test getting category by ID."""
        category_data = CategoryCreate(
            name="Books",
            description="Books and literature",
            slug="books",
            is_active=True,
        )

        created_category = CategoryService.create_category(db_session, category_data)
        retrieved_category = CategoryService.get_category(
            db_session, created_category.id
        )

        assert retrieved_category is not None
        assert retrieved_category.id == created_category.id
        assert retrieved_category.name == "Books"

    def test_get_nonexistent_category(self, db_session: Session):
        """Test getting non-existent category."""
        category = CategoryService.get_category(db_session, 999)
        assert category is None

    def test_get_category_by_slug(self, db_session: Session):
        """Test getting category by slug."""
        category_data = CategoryCreate(
            name="Clothing",
            description="Apparel and accessories",
            slug="clothing",
            is_active=True,
        )

        created_category = CategoryService.create_category(db_session, category_data)
        retrieved_category = CategoryService.get_category_by_slug(
            db_session, "clothing"
        )

        assert retrieved_category is not None
        assert retrieved_category.id == created_category.id
        assert retrieved_category.slug == "clothing"

    def test_get_categories_pagination(self, db_session: Session):
        """Test getting categories with pagination."""
        # Create multiple categories
        for i in range(15):
            category_data = CategoryCreate(
                name=f"Category {i}",
                description=f"Description {i}",
                slug=f"category-{i}",
                is_active=True,
            )
            CategoryService.create_category(db_session, category_data)

        # Test pagination
        result = CategoryService.get_categories(db_session, skip=0, limit=10)

        assert len(result.items) == 10
        assert result.total == 15
        assert result.page == 1
        assert result.pages == 2

        # Test second page
        result_page_2 = CategoryService.get_categories(db_session, skip=10, limit=10)

        assert len(result_page_2.items) == 5
        assert result_page_2.total == 15
        assert result_page_2.page == 2

    def test_get_categories_active_filter(self, db_session: Session):
        """Test filtering categories by active status."""
        # Create active category
        active_data = CategoryCreate(
            name="Active Category",
            description="Active category",
            slug="active-category",
            is_active=True,
        )
        CategoryService.create_category(db_session, active_data)

        # Create inactive category
        inactive_data = CategoryCreate(
            name="Inactive Category",
            description="Inactive category",
            slug="inactive-category",
            is_active=False,
        )
        CategoryService.create_category(db_session, inactive_data)

        # Test active only filter
        active_result = CategoryService.get_categories(db_session, active_only=True)
        assert len(active_result.items) == 1
        assert active_result.items[0].name == "Active Category"

        # Test all categories
        all_result = CategoryService.get_categories(db_session, active_only=False)
        assert len(all_result.items) == 2

    def test_get_categories_search(self, db_session: Session):
        """Test searching categories."""
        # Create test categories
        categories = [
            CategoryCreate(
                name="Electronics",
                description="Electronic devices",
                slug="electronics",
                is_active=True,
            ),
            CategoryCreate(
                name="Books",
                description="Books and literature",
                slug="books",
                is_active=True,
            ),
            CategoryCreate(
                name="Electronic Music",
                description="Music electronics",
                slug="electronic-music",
                is_active=True,
            ),
        ]

        for category_data in categories:
            CategoryService.create_category(db_session, category_data)

        # Search by name
        result = CategoryService.get_categories(db_session, search="electronic")
        assert len(result.items) == 2

        # Search by description
        result = CategoryService.get_categories(db_session, search="literature")
        assert len(result.items) == 1
        assert result.items[0].name == "Books"

    def test_update_category(self, db_session: Session):
        """Test updating category."""
        category_data = CategoryCreate(
            name="Original Name",
            description="Original description",
            slug="original-slug",
            is_active=True,
        )

        created_category = CategoryService.create_category(db_session, category_data)

        # Update category
        update_data = CategoryUpdate(
            name="Updated Name", description="Updated description", is_active=False
        )

        updated_category = CategoryService.update_category(
            db_session, created_category.id, update_data
        )

        assert updated_category.name == "Updated Name"
        assert updated_category.description == "Updated description"
        assert updated_category.is_active is False
        assert updated_category.slug == "original-slug"  # Should remain unchanged

    def test_update_nonexistent_category(self, db_session: Session):
        """Test updating non-existent category."""
        update_data = CategoryUpdate(name="New Name")

        with pytest.raises(Exception):
            CategoryService.update_category(db_session, 999, update_data)

    def test_delete_category(self, db_session: Session):
        """Test deleting category."""
        category_data = CategoryCreate(
            name="To Delete",
            description="Category to delete",
            slug="to-delete",
            is_active=True,
        )

        created_category = CategoryService.create_category(db_session, category_data)
        category_id = created_category.id

        # Delete category
        result = CategoryService.delete_category(db_session, category_id)
        assert result is True

        # Verify deletion
        deleted_category = CategoryService.get_category(db_session, category_id)
        assert deleted_category is None

    def test_delete_nonexistent_category(self, db_session: Session):
        """Test deleting non-existent category."""
        with pytest.raises(Exception):
            CategoryService.delete_category(db_session, 999)

    def test_get_active_categories(self, db_session: Session):
        """Test getting all active categories."""
        # Create mix of active and inactive categories
        categories = [
            CategoryCreate(name="Active 1", slug="active-1", is_active=True),
            CategoryCreate(name="Active 2", slug="active-2", is_active=True),
            CategoryCreate(name="Inactive 1", slug="inactive-1", is_active=False),
        ]

        for category_data in categories:
            CategoryService.create_category(db_session, category_data)

        active_categories = CategoryService.get_active_categories(db_session)

        assert len(active_categories) == 2
        assert all(cat.is_active for cat in active_categories)
        assert active_categories[0].name == "Active 1"
        assert active_categories[1].name == "Active 2"


class TestCategoryEndpoints:
    """
    Test cases for Category API endpoints.
    """

    def test_create_category_admin(self, client: TestClient, admin_auth_headers: dict):
        """Test creating category as admin."""
        category_data = {
            "name": "Test Category",
            "description": "Test description",
            "slug": "test-category",
            "is_active": True,
        }

        response = client.post(
            "/api/v1/categories/", json=category_data, headers=admin_auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Category"
        assert data["slug"] == "test-category"
        assert data["id"] is not None

    def test_create_category_non_admin(self, client: TestClient, auth_headers: dict):
        """Test creating category as non-admin user."""
        category_data = {
            "name": "Test Category",
            "description": "Test description",
            "slug": "test-category",
            "is_active": True,
        }

        response = client.post(
            "/api/v1/categories/", json=category_data, headers=auth_headers
        )

        assert response.status_code == 403

    def test_create_category_unauthenticated(self, client: TestClient):
        """Test creating category without authentication."""
        category_data = {
            "name": "Test Category",
            "description": "Test description",
            "slug": "test-category",
            "is_active": True,
        }

        response = client.post("/api/v1/categories/", json=category_data)
        assert response.status_code == 403

    def test_get_categories_public(self, client: TestClient, db_session: Session):
        """Test getting categories without authentication."""
        # Create test category
        category_data = CategoryCreate(
            name="Public Category",
            description="Public description",
            slug="public-category",
            is_active=True,
        )
        CategoryService.create_category(db_session, category_data)

        response = client.get("/api/v1/categories/")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert len(data["items"]) >= 1

    def test_get_categories_with_pagination(
        self, client: TestClient, db_session: Session
    ):
        """Test getting categories with pagination parameters."""
        response = client.get("/api/v1/categories/?skip=0&limit=5")

        assert response.status_code == 200
        data = response.json()
        assert data["size"] == 5
        assert data["page"] == 1

    def test_get_categories_with_search(self, client: TestClient, db_session: Session):
        """Test getting categories with search parameter."""
        # Create test category
        category_data = CategoryCreate(
            name="Searchable Category",
            description="Searchable description",
            slug="searchable-category",
            is_active=True,
        )
        CategoryService.create_category(db_session, category_data)

        response = client.get("/api/v1/categories/?search=searchable")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1

    def test_get_category_by_id(self, client: TestClient, db_session: Session):
        """Test getting category by ID."""
        category_data = CategoryCreate(
            name="Get by ID",
            description="Get by ID description",
            slug="get-by-id",
            is_active=True,
        )
        created_category = CategoryService.create_category(db_session, category_data)

        response = client.get(f"/api/v1/categories/{created_category.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_category.id
        assert data["name"] == "Get by ID"

    def test_get_category_by_slug(self, client: TestClient, db_session: Session):
        """Test getting category by slug."""
        category_data = CategoryCreate(
            name="Get by Slug",
            description="Get by slug description",
            slug="get-by-slug",
            is_active=True,
        )
        CategoryService.create_category(db_session, category_data)

        response = client.get("/api/v1/categories/slug/get-by-slug")

        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "get-by-slug"
        assert data["name"] == "Get by Slug"

    def test_get_active_categories_endpoint(
        self, client: TestClient, db_session: Session
    ):
        """Test getting active categories endpoint."""
        response = client.get("/api/v1/categories/active")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_update_category_admin(
        self, client: TestClient, admin_auth_headers: dict, db_session: Session
    ):
        """Test updating category as admin."""
        # Create category
        category_data = CategoryCreate(
            name="Original Name",
            description="Original description",
            slug="original-slug",
            is_active=True,
        )
        created_category = CategoryService.create_category(db_session, category_data)

        # Update category
        update_data = {"name": "Updated Name", "description": "Updated description"}

        response = client.put(
            f"/api/v1/categories/{created_category.id}",
            json=update_data,
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"

    def test_update_category_non_admin(
        self, client: TestClient, auth_headers: dict, db_session: Session
    ):
        """Test updating category as non-admin user."""
        category_data = CategoryCreate(
            name="Test Category", slug="test-category", is_active=True
        )
        created_category = CategoryService.create_category(db_session, category_data)

        update_data = {"name": "Updated Name"}

        response = client.put(
            f"/api/v1/categories/{created_category.id}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 403

    def test_delete_category_admin(
        self, client: TestClient, admin_auth_headers: dict, db_session: Session
    ):
        """Test deleting category as admin."""
        category_data = CategoryCreate(
            name="To Delete", slug="to-delete", is_active=True
        )
        created_category = CategoryService.create_category(db_session, category_data)

        response = client.delete(
            f"/api/v1/categories/{created_category.id}", headers=admin_auth_headers
        )

        assert response.status_code == 204

    def test_delete_category_non_admin(
        self, client: TestClient, auth_headers: dict, db_session: Session
    ):
        """Test deleting category as non-admin user."""
        category_data = CategoryCreate(
            name="Test Category", slug="test-category", is_active=True
        )
        created_category = CategoryService.create_category(db_session, category_data)

        response = client.delete(
            f"/api/v1/categories/{created_category.id}", headers=auth_headers
        )

        assert response.status_code == 403

    def test_get_nonexistent_category(self, client: TestClient):
        """Test getting non-existent category."""
        response = client.get("/api/v1/categories/999")
        assert response.status_code == 404

    def test_update_nonexistent_category(
        self, client: TestClient, admin_auth_headers: dict
    ):
        """Test updating non-existent category."""
        update_data = {"name": "Updated Name"}

        response = client.put(
            "/api/v1/categories/999", json=update_data, headers=admin_auth_headers
        )

        assert response.status_code == 404

    def test_delete_nonexistent_category(
        self, client: TestClient, admin_auth_headers: dict
    ):
        """Test deleting non-existent category."""
        response = client.delete("/api/v1/categories/999", headers=admin_auth_headers)

        assert response.status_code == 404
