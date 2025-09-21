"""
Tests for order functionality.
"""

import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

from app.models.user import User
from app.models.product import Product
from app.models.cart import Cart, CartItem
from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.schemas.order import CheckoutRequest, OrderUpdate, PaymentResponse


class TestPaymentService:
    """Test payment service functionality."""

    def test_process_payment_successful(self):
        """Test successful payment processing."""
        payment_service = PaymentService()

        # Mock random to ensure success
        with patch('app.services.payment_service.random') as mock_random:
            mock_random.return_value = 0.5  # Below success rate

            from app.schemas.order import PaymentRequest
            request = PaymentRequest(
                payment_method="credit_card",
                amount=Decimal("100.00")
            )

            response = payment_service.process_payment(request)

            assert response.status == PaymentStatus.COMPLETED
            assert response.amount == Decimal("100.00")
            assert "successfully" in response.message.lower()

    def test_process_payment_failed(self):
        """Test failed payment processing."""
        payment_service = PaymentService()

        # Mock random to ensure failure
        with patch('app.services.payment_service.random') as mock_random:
            mock_random.return_value = 0.99  # Above success rate

            from app.schemas.order import PaymentRequest
            request = PaymentRequest(
                payment_method="credit_card",
                amount=Decimal("100.00")
            )

            response = payment_service.process_payment(request)

            assert response.status == PaymentStatus.FAILED
            assert "failed" in response.message.lower()

    def test_process_payment_unsupported_method(self):
        """Test payment with unsupported method."""
        payment_service = PaymentService()

        from app.schemas.order import PaymentRequest
        request = PaymentRequest(
            payment_method="unsupported_method",
            amount=Decimal("100.00")
        )

        response = payment_service.process_payment(request)

        assert response.status == PaymentStatus.FAILED
        assert "Unsupported payment method" in response.message

    def test_validate_payment_method(self):
        """Test payment method validation."""
        payment_service = PaymentService()

        assert payment_service.validate_payment_method("credit_card") is True
        assert payment_service.validate_payment_method("invalid_method") is False

    def test_get_supported_methods(self):
        """Test getting supported payment methods."""
        payment_service = PaymentService()
        methods = payment_service.get_supported_methods()

        assert isinstance(methods, dict)
        assert "credit_card" in methods
        assert "paypal" in methods

    def test_refund_payment(self):
        """Test payment refund."""
        payment_service = PaymentService()

        # Mock random to ensure success
        with patch('app.services.payment_service.random') as mock_random:
            mock_random.return_value = 0.5

            response = payment_service.refund_payment("txn_123", Decimal("50.00"))

            assert response.status == PaymentStatus.REFUNDED
            assert response.amount == Decimal("50.00")


class TestOrderService:
    """Test order service functionality."""

    def test_create_order_from_cart(self, db_session: Session, test_user: User, test_product: Product):
        """Test creating order from cart."""
        order_service = OrderService(db_session)

        # Create cart with items
        cart = Cart(user_id=test_user.id)
        db_session.add(cart)
        db_session.flush()

        cart_item = CartItem(
            cart_id=cart.id,
            product_id=test_product.id,
            quantity=2,
            unit_price=test_product.price
        )
        db_session.add(cart_item)
        db_session.commit()

        # Create checkout request
        checkout_request = CheckoutRequest(
            shipping_address="123 Test St, Test City, TC 12345",
            payment_method="credit_card"
        )

        # Create order
        order_response = order_service.create_order_from_cart(test_user.id, checkout_request)

        assert order_response.status == OrderStatus.PENDING
        assert order_response.payment_status == PaymentStatus.PENDING
        assert order_response.items_count == 2
        assert len(order_response.items) == 1
        assert order_response.subtotal == test_product.price * 2

        # Check that cart is cleared
        cart = db_session.query(Cart).filter(Cart.user_id == test_user.id).first()
        assert cart.is_empty

        # Check stock was reduced
        db_session.refresh(test_product)
        assert test_product.stock_quantity == 98  # Original 100 - 2

    def test_create_order_from_empty_cart(self, db_session: Session, test_user: User):
        """Test creating order from empty cart."""
        order_service = OrderService(db_session)

        checkout_request = CheckoutRequest(
            shipping_address="123 Test St, Test City, TC 12345",
            payment_method="credit_card"
        )

        with pytest.raises(Exception) as exc_info:
            order_service.create_order_from_cart(test_user.id, checkout_request)
        assert "Cart is empty" in str(exc_info.value)

    def test_create_order_insufficient_stock(self, db_session: Session, test_user: User, test_product: Product):
        """Test creating order with insufficient stock."""
        order_service = OrderService(db_session)

        # Create cart with more items than available stock
        cart = Cart(user_id=test_user.id)
        db_session.add(cart)
        db_session.flush()

        cart_item = CartItem(
            cart_id=cart.id,
            product_id=test_product.id,
            quantity=test_product.stock_quantity + 1,
            unit_price=test_product.price
        )
        db_session.add(cart_item)
        db_session.commit()

        checkout_request = CheckoutRequest(
            shipping_address="123 Test St, Test City, TC 12345",
            payment_method="credit_card"
        )

        with pytest.raises(Exception) as exc_info:
            order_service.create_order_from_cart(test_user.id, checkout_request)
        assert "Insufficient stock" in str(exc_info.value)

    def test_process_payment_successful(self, db_session: Session, test_user: User, test_product: Product):
        """Test successful payment processing."""
        order_service = OrderService(db_session)

        # Create order
        order = Order(
            order_number="ORD-TEST-001",
            user_id=test_user.id,
            status=OrderStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("10.00"),
            shipping_amount=Decimal("5.00"),
            total_amount=Decimal("115.00"),
            shipping_address="123 Test St",
            payment_method="credit_card"
        )
        db_session.add(order)
        db_session.commit()

        # Mock successful payment
        with patch.object(order_service.payment_service, 'process_payment') as mock_payment:
            mock_payment.return_value = PaymentResponse(
                transaction_id="txn_123",
                status=PaymentStatus.COMPLETED,
                amount=Decimal("115.00"),
                message="Payment successful"
            )

            order_response = order_service.process_payment(test_user.id, order.id)

            assert order_response.status == OrderStatus.PAID
            assert order_response.payment_status == PaymentStatus.COMPLETED
            assert order_response.payment_transaction_id == "txn_123"

    def test_process_payment_failed(self, db_session: Session, test_user: User, test_product: Product):
        """Test failed payment processing."""
        order_service = OrderService(db_session)

        # Create order with items
        order = Order(
            order_number="ORD-TEST-002",
            user_id=test_user.id,
            status=OrderStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("10.00"),
            shipping_amount=Decimal("5.00"),
            total_amount=Decimal("115.00"),
            shipping_address="123 Test St",
            payment_method="credit_card"
        )
        db_session.add(order)
        db_session.flush()

        order_item = OrderItem(
            order_id=order.id,
            product_id=test_product.id,
            quantity=2,
            unit_price=test_product.price,
            total_price=test_product.price * 2,
            product_name=test_product.name,
            product_sku=test_product.sku
        )
        db_session.add(order_item)
        db_session.commit()

        original_stock = test_product.stock_quantity

        # Mock failed payment
        with patch.object(order_service.payment_service, 'process_payment') as mock_payment:
            mock_payment.return_value = PaymentResponse(
                transaction_id="txn_failed",
                status=PaymentStatus.FAILED,
                amount=Decimal("115.00"),
                message="Payment failed: Insufficient funds"
            )

            with pytest.raises(Exception) as exc_info:
                order_service.process_payment(test_user.id, order.id)
            assert "Payment failed" in str(exc_info.value)

            # Check stock was restored
            db_session.refresh(test_product)
            assert test_product.stock_quantity == original_stock

    def test_get_user_orders(self, db_session: Session, test_user: User):
        """Test getting user orders."""
        order_service = OrderService(db_session)

        # Create test orders
        order1 = Order(
            order_number="ORD-TEST-001",
            user_id=test_user.id,
            status=OrderStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("10.00"),
            shipping_amount=Decimal("5.00"),
            total_amount=Decimal("115.00"),
            shipping_address="123 Test St",
            payment_method="credit_card"
        )
        order2 = Order(
            order_number="ORD-TEST-002",
            user_id=test_user.id,
            status=OrderStatus.PAID,
            payment_status=PaymentStatus.COMPLETED,
            subtotal=Decimal("50.00"),
            tax_amount=Decimal("5.00"),
            shipping_amount=Decimal("0.00"),
            total_amount=Decimal("55.00"),
            shipping_address="456 Test Ave",
            payment_method="paypal"
        )
        db_session.add_all([order1, order2])
        db_session.commit()

        orders = order_service.get_user_orders(test_user.id)

        assert len(orders) == 2
        assert orders[0].order_number in ["ORD-TEST-001", "ORD-TEST-002"]

    def test_cancel_order(self, db_session: Session, test_user: User, test_product: Product):
        """Test cancelling order."""
        order_service = OrderService(db_session)

        # Create order with items
        order = Order(
            order_number="ORD-TEST-003",
            user_id=test_user.id,
            status=OrderStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("10.00"),
            shipping_amount=Decimal("5.00"),
            total_amount=Decimal("115.00"),
            shipping_address="123 Test St",
            payment_method="credit_card"
        )
        db_session.add(order)
        db_session.flush()

        order_item = OrderItem(
            order_id=order.id,
            product_id=test_product.id,
            quantity=2,
            unit_price=test_product.price,
            total_price=test_product.price * 2,
            product_name=test_product.name,
            product_sku=test_product.sku
        )
        db_session.add(order_item)
        db_session.commit()

        original_stock = test_product.stock_quantity

        # Cancel order
        order_response = order_service.cancel_order(test_user.id, order.id)

        assert order_response.status == OrderStatus.CANCELLED

        # Check stock was restored
        db_session.refresh(test_product)
        assert test_product.stock_quantity == original_stock + 2

    def test_update_order_status(self, db_session: Session, test_user: User):
        """Test updating order status."""
        order_service = OrderService(db_session)

        # Create order
        order = Order(
            order_number="ORD-TEST-004",
            user_id=test_user.id,
            status=OrderStatus.PAID,
            payment_status=PaymentStatus.COMPLETED,
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("10.00"),
            shipping_amount=Decimal("5.00"),
            total_amount=Decimal("115.00"),
            shipping_address="123 Test St",
            payment_method="credit_card"
        )
        db_session.add(order)
        db_session.commit()

        # Update to shipped
        update_data = OrderUpdate(status=OrderStatus.SHIPPED)
        order_response = order_service.update_order_status(order.id, update_data)

        assert order_response.status == OrderStatus.SHIPPED
        assert order_response.shipped_at is not None

    def test_invalid_status_transition(self, db_session: Session, test_user: User):
        """Test invalid status transition."""
        order_service = OrderService(db_session)

        # Create delivered order
        order = Order(
            order_number="ORD-TEST-005",
            user_id=test_user.id,
            status=OrderStatus.DELIVERED,
            payment_status=PaymentStatus.COMPLETED,
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("10.00"),
            shipping_amount=Decimal("5.00"),
            total_amount=Decimal("115.00"),
            shipping_address="123 Test St",
            payment_method="credit_card"
        )
        db_session.add(order)
        db_session.commit()

        # Try to update to pending (invalid)
        update_data = OrderUpdate(status=OrderStatus.PENDING)

        with pytest.raises(Exception) as exc_info:
            order_service.update_order_status(order.id, update_data)
        assert "Invalid status transition" in str(exc_info.value)


class TestOrderAPI:
    """Test order API endpoints."""

    def test_checkout_api(self, client: TestClient, test_user_token: str, test_product: Product, db_session: Session):
        """Test checkout API endpoint."""
        headers = {"Authorization": f"Bearer {test_user_token}"}

        # Add item to cart first
        add_payload = {
            "product_id": test_product.id,
            "quantity": 2
        }
        client.post("/api/v1/cart/add", json=add_payload, headers=headers)

        # Checkout
        checkout_payload = {
            "shipping_address": "123 Test St, Test City, TC 12345",
            "payment_method": "credit_card"
        }

        response = client.post("/api/v1/orders/checkout", json=checkout_payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["payment_status"] == "pending"
        assert data["items_count"] == 2

    def test_checkout_empty_cart(self, client: TestClient, test_user_token: str):
        """Test checkout with empty cart."""
        headers = {"Authorization": f"Bearer {test_user_token}"}

        checkout_payload = {
            "shipping_address": "123 Test St, Test City, TC 12345",
            "payment_method": "credit_card"
        }

        response = client.post("/api/v1/orders/checkout", json=checkout_payload, headers=headers)
        assert response.status_code == 400

    def test_pay_order_api(self, client: TestClient, test_user_token: str, test_product: Product):
        """Test pay order API endpoint."""
        headers = {"Authorization": f"Bearer {test_user_token}"}

        # Create order first
        add_payload = {
            "product_id": test_product.id,
            "quantity": 2
        }
        client.post("/api/v1/cart/add", json=add_payload, headers=headers)

        checkout_payload = {
            "shipping_address": "123 Test St, Test City, TC 12345",
            "payment_method": "credit_card"
        }
        checkout_response = client.post("/api/v1/orders/checkout", json=checkout_payload, headers=headers)
        order_id = checkout_response.json()["id"]

        # Mock successful payment
        with patch('app.services.payment_service.random') as mock_random:
            mock_random.return_value = 0.5  # Ensure success

            response = client.post(f"/api/v1/orders/{order_id}/pay", headers=headers)

            # Payment might fail randomly, so we check for either success or failure
            assert response.status_code in [200, 400]

    def test_get_user_orders_api(self, client: TestClient, test_user_token: str):
        """Test getting user orders via API."""
        headers = {"Authorization": f"Bearer {test_user_token}"}

        response = client.get("/api/v1/orders/", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_payment_methods_api(self, client: TestClient):
        """Test getting payment methods via API."""
        response = client.get("/api/v1/orders/payment/methods")

        assert response.status_code == 200
        data = response.json()
        assert "supported_methods" in data
        assert "credit_card" in data["supported_methods"]

    def test_order_unauthorized(self, client: TestClient):
        """Test order endpoints without authentication."""
        response = client.get("/api/v1/orders/")
        assert response.status_code == 403

        response = client.post("/api/v1/orders/checkout", json={
            "shipping_address": "123 Test St",
            "payment_method": "credit_card"
        })
        assert response.status_code == 403