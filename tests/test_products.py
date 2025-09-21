"""
Comprehensive tests for Products functionality.
"""

import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.product import Product
from app.models.category import Category
from app.models.user import User
from app.schemas.product import ProductCreate, ProductUpdate, ProductFilters, StockUpdate
from app.schemas.category import CategoryCreate
from app.services.product import ProductService
from app.services.category import CategoryService


class TestProductService:
    """
    Test cases for ProductService.
    """

    def test_create_product(self, db_session: Session):
        """Test creating a new product."""
        product_data = ProductCreate(
            name="Test Product",
            description="Test product description",
            slug="test-product",
            sku="TEST-001",
            price=Decimal("99.99"),
            stock_quantity=50,
            is_active=True
        )

        product = ProductService.create_product(db_session, product_data)

        assert product.id is not None
        assert product.name == "Test Product"
        assert product.slug == "test-product"
        assert product.sku == "TEST-001"
        assert product.price == Decimal("99.99")
        assert product.stock_quantity == 50
        assert product.is_active is True
        assert product.created_at is not None

    def test_create_product_with_category(self, db_session: Session):
        """Test creating product with category."""
        # Create category first
        category_data = CategoryCreate(
            name="Electronics",
            slug="electronics",
            is_active=True
        )
        category = CategoryService.create_category(db_session, category_data)

        product_data = ProductCreate(
            name="Smartphone",
            description="Latest smartphone",
            slug="smartphone",
            sku="PHONE-001",
            price=Decimal("599.99"),
            stock_quantity=25,
            category_id=category.id,
            is_active=True
        )

        product = ProductService.create_product(db_session, product_data)

        assert product.category_id == category.id
        assert product.category.name == "Electronics"

    def test_create_product_invalid_category(self, db_session: Session):
        """Test creating product with invalid category."""
        product_data = ProductCreate(
            name="Test Product",
            slug="test-product",
            sku="TEST-001",
            price=Decimal("99.99"),
            category_id=999,  # Non-existent category
            is_active=True
        )

        with pytest.raises(Exception):
            ProductService.create_product(db_session, product_data)

    def test_create_duplicate_sku(self, db_session: Session):
        """Test creating product with duplicate SKU."""
        product_data = ProductCreate(
            name="Product 1",
            slug="product-1",
            sku="DUPLICATE-001",
            price=Decimal("99.99"),
            is_active=True
        )

        # Create first product
        ProductService.create_product(db_session, product_data)

        # Try to create duplicate SKU
        duplicate_data = ProductCreate(
            name="Product 2",
            slug="product-2",
            sku="DUPLICATE-001",  # Same SKU
            price=Decimal("199.99"),
            is_active=True
        )

        with pytest.raises(Exception):
            ProductService.create_product(db_session, duplicate_data)

    def test_create_duplicate_slug(self, db_session: Session):
        """Test creating product with duplicate slug."""
        product_data = ProductCreate(
            name="Product 1",
            slug="duplicate-slug",
            sku="SKU-001",
            price=Decimal("99.99"),
            is_active=True
        )

        # Create first product
        ProductService.create_product(db_session, product_data)

        # Try to create duplicate slug
        duplicate_data = ProductCreate(
            name="Product 2",
            slug="duplicate-slug",  # Same slug
            sku="SKU-002",
            price=Decimal("199.99"),
            is_active=True
        )

        with pytest.raises(Exception):
            ProductService.create_product(db_session, duplicate_data)

    def test_get_product(self, db_session: Session):
        """Test getting product by ID."""
        product_data = ProductCreate(
            name="Get Test Product",
            slug="get-test-product",
            sku="GET-001",
            price=Decimal("149.99"),
            is_active=True
        )

        created_product = ProductService.create_product(db_session, product_data)
        retrieved_product = ProductService.get_product(db_session, created_product.id)

        assert retrieved_product is not None
        assert retrieved_product.id == created_product.id
        assert retrieved_product.name == "Get Test Product"

    def test_get_product_by_slug(self, db_session: Session):
        """Test getting product by slug."""
        product_data = ProductCreate(
            name="Slug Test Product",
            slug="slug-test-product",
            sku="SLUG-001",
            price=Decimal("199.99"),
            is_active=True
        )

        created_product = ProductService.create_product(db_session, product_data)
        retrieved_product = ProductService.get_product_by_slug(db_session, "slug-test-product")

        assert retrieved_product is not None
        assert retrieved_product.id == created_product.id
        assert retrieved_product.slug == "slug-test-product"

    def test_get_product_by_sku(self, db_session: Session):
        """Test getting product by SKU."""
        product_data = ProductCreate(
            name="SKU Test Product",
            slug="sku-test-product",
            sku="SKU-TEST-001",
            price=Decimal("299.99"),
            is_active=True
        )

        created_product = ProductService.create_product(db_session, product_data)
        retrieved_product = ProductService.get_product_by_sku(db_session, "SKU-TEST-001")

        assert retrieved_product is not None
        assert retrieved_product.id == created_product.id
        assert retrieved_product.sku == "SKU-TEST-001"

    def test_get_products_pagination(self, db_session: Session):
        """Test getting products with pagination."""
        # Create multiple products
        for i in range(15):
            product_data = ProductCreate(
                name=f"Product {i}",
                slug=f"product-{i}",
                sku=f"SKU-{i:03d}",
                price=Decimal(f"{100 + i}.99"),
                is_active=True
            )
            ProductService.create_product(db_session, product_data)

        # Test first page
        result = ProductService.get_products(db_session, skip=0, limit=10)

        assert len(result.items) == 10
        assert result.total == 15
        assert result.page == 1
        assert result.pages == 2

        # Test second page
        result_page_2 = ProductService.get_products(db_session, skip=10, limit=10)

        assert len(result_page_2.items) == 5
        assert result_page_2.total == 15
        assert result_page_2.page == 2

    def test_get_products_with_filters(self, db_session: Session):
        """Test getting products with various filters."""
        # Create category
        category_data = CategoryCreate(name="Test Category", slug="test-category", is_active=True)
        category = CategoryService.create_category(db_session, category_data)

        # Create products with different attributes
        products = [
            ProductCreate(
                name="Expensive Product", slug="expensive", sku="EXP-001",
                price=Decimal("999.99"), stock_quantity=10, is_featured=True,
                category_id=category.id, is_active=True
            ),
            ProductCreate(
                name="Cheap Product", slug="cheap", sku="CHEAP-001",
                price=Decimal("19.99"), stock_quantity=0, is_featured=False,
                is_active=True
            ),
            ProductCreate(
                name="Inactive Product", slug="inactive", sku="INACTIVE-001",
                price=Decimal("49.99"), stock_quantity=5, is_active=False
            ),
        ]

        for product_data in products:
            ProductService.create_product(db_session, product_data)

        # Test price range filter
        filters = ProductFilters(min_price=Decimal("50.00"), max_price=Decimal("1000.00"))
        result = ProductService.get_products(db_session, filters=filters)
        assert len(result.items) == 1
        assert result.items[0].name == "Expensive Product"

        # Test category filter
        filters = ProductFilters(category_id=category.id)
        result = ProductService.get_products(db_session, filters=filters)
        assert len(result.items) == 1
        assert result.items[0].category.id == category.id

        # Test stock filter - only active products with stock > 0
        filters = ProductFilters(in_stock=True)
        result = ProductService.get_products(db_session, filters=filters)
        assert len(result.items) == 1  # Only "Expensive Product" (stock=10, active=True)
        assert all(item.stock_quantity > 0 for item in result.items)

        # Test featured filter
        filters = ProductFilters(is_featured=True)
        result = ProductService.get_products(db_session, filters=filters)
        assert len(result.items) == 1
        assert result.items[0].is_featured is True

        # Test search filter
        filters = ProductFilters(search="expensive")
        result = ProductService.get_products(db_session, filters=filters)
        assert len(result.items) == 1
        assert "expensive" in result.items[0].name.lower()

    def test_update_product(self, db_session: Session):
        """Test updating product."""
        product_data = ProductCreate(
            name="Original Product",
            slug="original-product",
            sku="ORIG-001",
            price=Decimal("99.99"),
            stock_quantity=20,
            is_active=True
        )

        created_product = ProductService.create_product(db_session, product_data)

        # Update product
        update_data = ProductUpdate(
            name="Updated Product",
            price=Decimal("149.99"),
            stock_quantity=30,
            is_featured=True
        )

        updated_product = ProductService.update_product(
            db_session, created_product.id, update_data
        )

        assert updated_product.name == "Updated Product"
        assert updated_product.price == Decimal("149.99")
        assert updated_product.stock_quantity == 30
        assert updated_product.is_featured is True
        assert updated_product.slug == "original-product"  # Should remain unchanged

    def test_update_stock(self, db_session: Session):
        """Test updating product stock."""
        product_data = ProductCreate(
            name="Stock Test Product",
            slug="stock-test",
            sku="STOCK-001",
            price=Decimal("99.99"),
            stock_quantity=20,
            low_stock_threshold=10,
            is_active=True
        )

        created_product = ProductService.create_product(db_session, product_data)

        # Update stock
        stock_data = StockUpdate(
            stock_quantity=50,
            low_stock_threshold=15
        )

        updated_product = ProductService.update_stock(
            db_session, created_product.id, stock_data
        )

        assert updated_product.stock_quantity == 50
        assert updated_product.low_stock_threshold == 15

    def test_delete_product(self, db_session: Session):
        """Test deleting product."""
        product_data = ProductCreate(
            name="To Delete",
            slug="to-delete",
            sku="DELETE-001",
            price=Decimal("99.99"),
            is_active=True
        )

        created_product = ProductService.create_product(db_session, product_data)
        product_id = created_product.id

        # Delete product
        result = ProductService.delete_product(db_session, product_id)
        assert result is True

        # Verify deletion
        deleted_product = ProductService.get_product(db_session, product_id)
        assert deleted_product is None

    def test_get_featured_products(self, db_session: Session):
        """Test getting featured products."""
        # Create mix of featured and non-featured products
        products = [
            ProductCreate(name="Featured 1", slug="featured-1", sku="FEAT-001", price=Decimal("99.99"), is_featured=True, is_active=True),
            ProductCreate(name="Featured 2", slug="featured-2", sku="FEAT-002", price=Decimal("149.99"), is_featured=True, is_active=True),
            ProductCreate(name="Regular", slug="regular", sku="REG-001", price=Decimal("79.99"), is_featured=False, is_active=True),
        ]

        for product_data in products:
            ProductService.create_product(db_session, product_data)

        featured_products = ProductService.get_featured_products(db_session, limit=10)

        assert len(featured_products) == 2
        assert all(product.is_featured for product in featured_products)

    def test_get_low_stock_products(self, db_session: Session):
        """Test getting low stock products."""
        # Create products with different stock levels
        products = [
            ProductCreate(name="Low Stock 1", slug="low-1", sku="LOW-001", price=Decimal("99.99"), stock_quantity=5, low_stock_threshold=10, is_active=True),
            ProductCreate(name="Low Stock 2", slug="low-2", sku="LOW-002", price=Decimal("149.99"), stock_quantity=3, low_stock_threshold=10, is_active=True),
            ProductCreate(name="Good Stock", slug="good", sku="GOOD-001", price=Decimal("79.99"), stock_quantity=50, low_stock_threshold=10, is_active=True),
        ]

        for product_data in products:
            ProductService.create_product(db_session, product_data)

        low_stock_products = ProductService.get_low_stock_products(db_session, limit=10)

        assert len(low_stock_products) == 2
        assert all(product.stock_quantity <= product.low_stock_threshold for product in low_stock_products)

    def test_search_products(self, db_session: Session):
        """Test searching products."""
        # Create products for search testing
        products = [
            ProductCreate(name="Apple iPhone", slug="iphone", sku="APPLE-001", price=Decimal("999.99"), description="Latest Apple smartphone", is_active=True),
            ProductCreate(name="Samsung Galaxy", slug="galaxy", sku="SAMSUNG-001", price=Decimal("899.99"), description="Android smartphone", is_active=True),
            ProductCreate(name="Apple MacBook", slug="macbook", sku="APPLE-002", price=Decimal("1299.99"), description="Apple laptop", is_active=True),
        ]

        for product_data in products:
            ProductService.create_product(db_session, product_data)

        # Search by name
        results = ProductService.search_products(db_session, "Apple", limit=10)
        assert len(results) == 2
        assert all("Apple" in product.name for product in results)

        # Search by description
        results = ProductService.search_products(db_session, "smartphone", limit=10)
        assert len(results) == 2

        # Search by SKU
        results = ProductService.search_products(db_session, "SAMSUNG", limit=10)
        assert len(results) == 1
        assert results[0].name == "Samsung Galaxy"

    def test_product_properties(self, db_session: Session):
        """Test product model properties."""
        # Test is_on_sale property
        product_data = ProductCreate(
            name="Sale Product",
            slug="sale-product",
            sku="SALE-001",
            price=Decimal("99.99"),
            compare_price=Decimal("149.99"),
            stock_quantity=10,
            is_active=True
        )

        product = ProductService.create_product(db_session, product_data)

        assert product.is_on_sale is True
        assert product.discount_percentage == 33.34

        # Test is_in_stock property
        assert product.is_in_stock is True

        # Test is_low_stock property (default threshold is 10)
        assert product.is_low_stock is True

        # Test can_order method
        assert product.can_order(5) is True
        assert product.can_order(15) is False


class TestProductEndpoints:
    """
    Test cases for Product API endpoints.
    """

    def test_create_product_admin(self, client: TestClient, admin_auth_headers: dict):
        """Test creating product as admin."""
        product_data = {
            "name": "Test Product",
            "description": "Test description",
            "slug": "test-product",
            "sku": "TEST-001",
            "price": "99.99",
            "stock_quantity": 50,
            "is_active": True
        }

        response = client.post(
            "/api/v1/products/",
            json=product_data,
            headers=admin_auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Product"
        assert data["sku"] == "TEST-001"
        assert data["id"] is not None

    def test_create_product_non_admin(self, client: TestClient, auth_headers: dict):
        """Test creating product as non-admin user."""
        product_data = {
            "name": "Test Product",
            "slug": "test-product",
            "sku": "TEST-001",
            "price": "99.99",
            "is_active": True
        }

        response = client.post(
            "/api/v1/products/",
            json=product_data,
            headers=auth_headers
        )

        assert response.status_code == 403

    def test_get_products_public(self, client: TestClient, db_session: Session):
        """Test getting products without authentication."""
        # Create test product
        product_data = ProductCreate(
            name="Public Product",
            slug="public-product",
            sku="PUBLIC-001",
            price=Decimal("99.99"),
            is_active=True
        )
        ProductService.create_product(db_session, product_data)

        response = client.get("/api/v1/products/")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 1

    def test_get_products_with_filters(self, client: TestClient, db_session: Session):
        """Test getting products with filter parameters."""
        # Create category and product
        category_data = CategoryCreate(name="Filter Category", slug="filter-category", is_active=True)
        category = CategoryService.create_category(db_session, category_data)

        product_data = ProductCreate(
            name="Filter Product",
            slug="filter-product",
            sku="FILTER-001",
            price=Decimal("199.99"),
            category_id=category.id,
            is_featured=True,
            is_active=True
        )
        ProductService.create_product(db_session, product_data)

        # Test various filters
        response = client.get(f"/api/v1/products/?category_id={category.id}")
        assert response.status_code == 200

        response = client.get("/api/v1/products/?min_price=100&max_price=300")
        assert response.status_code == 200

        response = client.get("/api/v1/products/?is_featured=true")
        assert response.status_code == 200

        response = client.get("/api/v1/products/?search=filter")
        assert response.status_code == 200

    def test_get_featured_products(self, client: TestClient, db_session: Session):
        """Test getting featured products endpoint."""
        response = client.get("/api/v1/products/featured")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_low_stock_products_admin(self, client: TestClient, admin_auth_headers: dict):
        """Test getting low stock products as admin."""
        response = client.get(
            "/api/v1/products/low-stock",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_low_stock_products_non_admin(self, client: TestClient, auth_headers: dict):
        """Test getting low stock products as non-admin."""
        response = client.get(
            "/api/v1/products/low-stock",
            headers=auth_headers
        )

        assert response.status_code == 403

    def test_search_products(self, client: TestClient, db_session: Session):
        """Test product search endpoint."""
        # Create searchable product
        product_data = ProductCreate(
            name="Searchable Product",
            slug="searchable-product",
            sku="SEARCH-001",
            price=Decimal("99.99"),
            is_active=True
        )
        ProductService.create_product(db_session, product_data)

        response = client.get("/api/v1/products/search?q=searchable")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_product_by_id(self, client: TestClient, db_session: Session):
        """Test getting product by ID."""
        product_data = ProductCreate(
            name="Get by ID Product",
            slug="get-by-id",
            sku="GET-001",
            price=Decimal("99.99"),
            is_active=True
        )
        created_product = ProductService.create_product(db_session, product_data)

        response = client.get(f"/api/v1/products/{created_product.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_product.id
        assert data["name"] == "Get by ID Product"

    def test_get_product_by_slug(self, client: TestClient, db_session: Session):
        """Test getting product by slug."""
        product_data = ProductCreate(
            name="Get by Slug Product",
            slug="get-by-slug",
            sku="SLUG-001",
            price=Decimal("99.99"),
            is_active=True
        )
        ProductService.create_product(db_session, product_data)

        response = client.get("/api/v1/products/slug/get-by-slug")

        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "get-by-slug"

    def test_get_product_by_sku_admin(self, client: TestClient, admin_auth_headers: dict, db_session: Session):
        """Test getting product by SKU as admin."""
        product_data = ProductCreate(
            name="SKU Product",
            slug="sku-product",
            sku="SKU-001",
            price=Decimal("99.99"),
            is_active=True
        )
        ProductService.create_product(db_session, product_data)

        response = client.get(
            "/api/v1/products/sku/SKU-001",
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["sku"] == "SKU-001"

    def test_update_product_admin(self, client: TestClient, admin_auth_headers: dict, db_session: Session):
        """Test updating product as admin."""
        product_data = ProductCreate(
            name="Update Product",
            slug="update-product",
            sku="UPDATE-001",
            price=Decimal("99.99"),
            is_active=True
        )
        created_product = ProductService.create_product(db_session, product_data)

        update_data = {
            "name": "Updated Product Name",
            "price": "149.99"
        }

        response = client.put(
            f"/api/v1/products/{created_product.id}",
            json=update_data,
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Product Name"
        assert float(data["price"]) == 149.99

    def test_update_product_stock_admin(self, client: TestClient, admin_auth_headers: dict, db_session: Session):
        """Test updating product stock as admin."""
        product_data = ProductCreate(
            name="Stock Product",
            slug="stock-product",
            sku="STOCK-001",
            price=Decimal("99.99"),
            stock_quantity=20,
            is_active=True
        )
        created_product = ProductService.create_product(db_session, product_data)

        stock_data = {
            "stock_quantity": 100,
            "low_stock_threshold": 15
        }

        response = client.patch(
            f"/api/v1/products/{created_product.id}/stock",
            json=stock_data,
            headers=admin_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["stock_quantity"] == 100
        assert data["low_stock_threshold"] == 15

    def test_delete_product_admin(self, client: TestClient, admin_auth_headers: dict, db_session: Session):
        """Test deleting product as admin."""
        product_data = ProductCreate(
            name="Delete Product",
            slug="delete-product",
            sku="DELETE-001",
            price=Decimal("99.99"),
            is_active=True
        )
        created_product = ProductService.create_product(db_session, product_data)

        response = client.delete(
            f"/api/v1/products/{created_product.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == 204

    def test_get_nonexistent_product(self, client: TestClient):
        """Test getting non-existent product."""
        response = client.get("/api/v1/products/999")
        assert response.status_code == 404

    def test_product_validation_errors(self, client: TestClient, admin_auth_headers: dict):
        """Test product validation errors."""
        # Test invalid price
        invalid_data = {
            "name": "Invalid Product",
            "slug": "invalid-product",
            "sku": "INVALID-001",
            "price": "-10.00",  # Negative price
            "is_active": True
        }

        response = client.post(
            "/api/v1/products/",
            json=invalid_data,
            headers=admin_auth_headers
        )

        assert response.status_code == 422  # Validation error