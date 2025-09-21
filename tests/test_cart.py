"""
Tests for cart functionality.
"""

import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.product import Product
from app.models.category import Category
from app.models.cart import Cart, CartItem
from app.services.cart_service import CartService
from app.schemas.cart import AddToCartRequest, UpdateCartItemRequest


class TestCartService:
    """Test cart service functionality."""

    def test_get_or_create_cart(self, db_session: Session, created_user: User):
        """Test getting or creating cart for user."""
        cart_service = CartService(db_session)

        # First call should create cart
        cart = cart_service.get_or_create_cart(created_user.id)
        assert cart is not None
        assert cart.user_id == created_user.id
        assert cart.is_empty

        # Second call should return existing cart
        cart2 = cart_service.get_or_create_cart(created_user.id)
        assert cart2.id == cart.id

    def test_add_to_cart_new_item(self, db_session: Session, created_user: User, test_product: Product):
        """Test adding new item to cart."""
        cart_service = CartService(db_session)
        request = AddToCartRequest(product_id=test_product.id, quantity=2)

        cart_response = cart_service.add_to_cart(created_user.id, request)

        assert cart_response.total_items == 2
        assert len(cart_response.items) == 1
        assert cart_response.items[0].product_id == test_product.id
        assert cart_response.items[0].quantity == 2
        assert cart_response.items[0].unit_price == test_product.price

    def test_add_to_cart_existing_item(self, db_session: Session, created_user: User, test_product: Product):
        """Test adding to existing cart item."""
        cart_service = CartService(db_session)

        # Add item first time
        request1 = AddToCartRequest(product_id=test_product.id, quantity=2)
        cart_service.add_to_cart(created_user.id, request1)

        # Add same item again
        request2 = AddToCartRequest(product_id=test_product.id, quantity=1)
        cart_response = cart_service.add_to_cart(created_user.id, request2)

        assert cart_response.total_items == 3
        assert len(cart_response.items) == 1
        assert cart_response.items[0].quantity == 3

    def test_add_to_cart_insufficient_stock(self, db_session: Session, created_user: User, test_product: Product):
        """Test adding item with insufficient stock."""
        cart_service = CartService(db_session)

        # Try to add more than available stock
        request = AddToCartRequest(product_id=test_product.id, quantity=test_product.stock_quantity + 1)

        with pytest.raises(Exception) as exc_info:
            cart_service.add_to_cart(created_user.id, request)
        assert "Insufficient stock" in str(exc_info.value)

    def test_add_to_cart_inactive_product(self, db_session: Session, created_user: User, test_product: Product):
        """Test adding inactive product to cart."""
        cart_service = CartService(db_session)

        # Make product inactive
        test_product.is_active = False
        db_session.commit()

        request = AddToCartRequest(product_id=test_product.id, quantity=1)

        with pytest.raises(Exception) as exc_info:
            cart_service.add_to_cart(created_user.id, request)
        assert "Product not found or inactive" in str(exc_info.value)

    def test_remove_from_cart(self, db_session: Session, created_user: User, test_product: Product):
        """Test removing item from cart."""
        cart_service = CartService(db_session)

        # Add item first
        request = AddToCartRequest(product_id=test_product.id, quantity=2)
        cart_service.add_to_cart(created_user.id, request)

        # Remove item
        cart_response = cart_service.remove_from_cart(created_user.id, test_product.id)

        assert cart_response.is_empty
        assert len(cart_response.items) == 0

    def test_remove_from_cart_nonexistent_item(self, db_session: Session, created_user: User):
        """Test removing non-existent item from cart."""
        cart_service = CartService(db_session)

        with pytest.raises(Exception) as exc_info:
            cart_service.remove_from_cart(created_user.id, 999)
        assert "Item not found in cart" in str(exc_info.value)

    def test_update_cart_item(self, db_session: Session, created_user: User, test_product: Product):
        """Test updating cart item quantity."""
        cart_service = CartService(db_session)

        # Add item first
        add_request = AddToCartRequest(product_id=test_product.id, quantity=2)
        cart_service.add_to_cart(created_user.id, add_request)

        # Update quantity
        update_request = UpdateCartItemRequest(quantity=5)
        cart_response = cart_service.update_cart_item(created_user.id, test_product.id, update_request)

        assert cart_response.total_items == 5
        assert cart_response.items[0].quantity == 5

    def test_update_cart_item_insufficient_stock(self, db_session: Session, created_user: User, test_product: Product):
        """Test updating cart item with insufficient stock."""
        cart_service = CartService(db_session)

        # Add item first
        add_request = AddToCartRequest(product_id=test_product.id, quantity=2)
        cart_service.add_to_cart(created_user.id, add_request)

        # Try to update to more than available stock
        update_request = UpdateCartItemRequest(quantity=test_product.stock_quantity + 1)

        with pytest.raises(Exception) as exc_info:
            cart_service.update_cart_item(created_user.id, test_product.id, update_request)
        assert "Insufficient stock" in str(exc_info.value)

    def test_clear_cart(self, db_session: Session, created_user: User, test_product: Product):
        """Test clearing all items from cart."""
        cart_service = CartService(db_session)

        # Add items first
        request = AddToCartRequest(product_id=test_product.id, quantity=2)
        cart_service.add_to_cart(created_user.id, request)

        # Clear cart
        cart_response = cart_service.clear_cart(created_user.id)

        assert cart_response.is_empty
        assert len(cart_response.items) == 0
        assert cart_response.total_items == 0

    def test_get_cart_summary(self, db_session: Session, created_user: User, test_product: Product):
        """Test getting cart summary."""
        cart_service = CartService(db_session)

        # Empty cart summary
        summary = cart_service.get_cart_summary(created_user.id)
        assert summary.total_items == 0
        assert summary.total_amount == Decimal('0.00')
        assert summary.items_count == 0

        # Add item and check summary
        request = AddToCartRequest(product_id=test_product.id, quantity=2)
        cart_service.add_to_cart(created_user.id, request)

        summary = cart_service.get_cart_summary(created_user.id)
        assert summary.total_items == 2
        assert summary.total_amount == test_product.price * 2
        assert summary.items_count == 1


class TestCartAPI:
    """Test cart API endpoints."""

    def test_get_empty_cart(self, client: TestClient, test_user_token: str):
        """Test getting empty cart."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = client.get("/api/v1/cart/", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["is_empty"] is True
        assert data["total_items"] == 0
        assert len(data["items"]) == 0

    def test_add_to_cart_api(self, client: TestClient, test_user_token: str, test_product: Product):
        """Test adding item to cart via API."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        payload = {
            "product_id": test_product.id,
            "quantity": 2
        }

        response = client.post("/api/v1/cart/add", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_items"] == 2
        assert len(data["items"]) == 1
        assert data["items"][0]["product_id"] == test_product.id

    def test_add_to_cart_invalid_product(self, client: TestClient, test_user_token: str):
        """Test adding non-existent product to cart."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        payload = {
            "product_id": 999,
            "quantity": 1
        }

        response = client.post("/api/v1/cart/add", json=payload, headers=headers)
        assert response.status_code == 404

    def test_add_to_cart_invalid_quantity(self, client: TestClient, test_user_token: str, test_product: Product):
        """Test adding item with invalid quantity."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        payload = {
            "product_id": test_product.id,
            "quantity": 0
        }

        response = client.post("/api/v1/cart/add", json=payload, headers=headers)
        assert response.status_code == 422

    def test_update_cart_item_api(self, client: TestClient, test_user_token: str, test_product: Product):
        """Test updating cart item via API."""
        headers = {"Authorization": f"Bearer {test_user_token}"}

        # Add item first
        add_payload = {
            "product_id": test_product.id,
            "quantity": 2
        }
        client.post("/api/v1/cart/add", json=add_payload, headers=headers)

        # Update item
        update_payload = {"quantity": 5}
        response = client.put(
            f"/api/v1/cart/items/{test_product.id}",
            json=update_payload,
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_items"] == 5

    def test_remove_from_cart_api(self, client: TestClient, test_user_token: str, test_product: Product):
        """Test removing item from cart via API."""
        headers = {"Authorization": f"Bearer {test_user_token}"}

        # Add item first
        add_payload = {
            "product_id": test_product.id,
            "quantity": 2
        }
        client.post("/api/v1/cart/add", json=add_payload, headers=headers)

        # Remove item
        response = client.delete(f"/api/v1/cart/items/{test_product.id}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["is_empty"] is True

    def test_clear_cart_api(self, client: TestClient, test_user_token: str, test_product: Product):
        """Test clearing cart via API."""
        headers = {"Authorization": f"Bearer {test_user_token}"}

        # Add item first
        add_payload = {
            "product_id": test_product.id,
            "quantity": 2
        }
        client.post("/api/v1/cart/add", json=add_payload, headers=headers)

        # Clear cart
        response = client.delete("/api/v1/cart/clear", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["is_empty"] is True

    def test_get_cart_summary_api(self, client: TestClient, test_user_token: str, test_product: Product):
        """Test getting cart summary via API."""
        headers = {"Authorization": f"Bearer {test_user_token}"}

        # Add item first
        add_payload = {
            "product_id": test_product.id,
            "quantity": 2
        }
        client.post("/api/v1/cart/add", json=add_payload, headers=headers)

        # Get summary
        response = client.get("/api/v1/cart/summary", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_items"] == 2
        assert data["items_count"] == 1

    def test_cart_unauthorized(self, client: TestClient):
        """Test cart endpoints without authentication."""
        response = client.get("/api/v1/cart/")
        assert response.status_code == 403

        response = client.post("/api/v1/cart/add", json={"product_id": 1, "quantity": 1})
        assert response.status_code == 403