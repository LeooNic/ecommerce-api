"""
Order service for managing order operations and workflow.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus
from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.models.user import User
from app.schemas.order import (
    OrderResponse,
    OrderItemResponse,
    OrderSummary,
    CheckoutRequest,
    OrderUpdate,
    PaymentRequest
)
from app.services.payment_service import PaymentService


class OrderService:
    """
    Service class for order operations.
    """

    def __init__(self, db: Session):
        """
        Initialize order service.

        Args:
            db: Database session
        """
        self.db = db
        self.payment_service = PaymentService()

    def create_order_from_cart(self, user_id: int, checkout_request: CheckoutRequest) -> OrderResponse:
        """
        Create order from user's cart.

        Args:
            user_id: User ID
            checkout_request: Checkout request details

        Returns:
            OrderResponse: Created order

        Raises:
            HTTPException: If cart is empty or validation fails
        """
        # Get user's cart
        cart = self.db.query(Cart).filter(Cart.user_id == user_id).first()
        if not cart or cart.is_empty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cart is empty"
            )

        # Validate all cart items have sufficient stock
        for cart_item in cart.items:
            product = cart_item.product
            if not product.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Product {product.name} is no longer available"
                )
            if not product.can_order(cart_item.quantity):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for {product.name}. Available: {product.stock_quantity}"
                )

        # Calculate totals
        subtotal = cart.total_amount
        tax_amount = subtotal * Decimal('0.10')  # 10% tax
        shipping_amount = Decimal('10.00') if subtotal < Decimal('100.00') else Decimal('0.00')
        total_amount = subtotal + tax_amount + shipping_amount

        # Generate order number
        order_number = self._generate_order_number()

        # Create order
        order = Order(
            order_number=order_number,
            user_id=user_id,
            status=OrderStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            subtotal=subtotal,
            tax_amount=tax_amount,
            shipping_amount=shipping_amount,
            total_amount=total_amount,
            shipping_address=checkout_request.shipping_address,
            billing_address=checkout_request.billing_address,
            phone=checkout_request.phone,
            notes=checkout_request.notes,
            payment_method=checkout_request.payment_method
        )

        self.db.add(order)
        self.db.flush()  # Get order ID

        # Create order items and update stock
        for cart_item in cart.items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=cart_item.product_id,
                quantity=cart_item.quantity,
                unit_price=cart_item.unit_price,
                total_price=cart_item.subtotal,
                product_name=cart_item.product.name,
                product_sku=cart_item.product.sku
            )
            self.db.add(order_item)

            # Update product stock
            product = cart_item.product
            product.stock_quantity -= cart_item.quantity

        # Clear cart
        self.db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()

        self.db.commit()
        self.db.refresh(order)

        return self._order_to_response(order)

    def process_payment(self, user_id: int, order_id: int) -> OrderResponse:
        """
        Process payment for an order.

        Args:
            user_id: User ID
            order_id: Order ID

        Returns:
            OrderResponse: Updated order

        Raises:
            HTTPException: If order not found or cannot be paid
        """
        order = self._get_user_order(user_id, order_id)

        if order.status != OrderStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order cannot be paid"
            )

        if order.payment_status != PaymentStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment has already been processed"
            )

        # Process payment
        payment_request = PaymentRequest(
            payment_method=order.payment_method,
            amount=order.total_amount
        )

        order.payment_status = PaymentStatus.PROCESSING
        self.db.commit()

        payment_response = self.payment_service.process_payment(payment_request)

        # Update order based on payment result
        order.payment_status = payment_response.status
        order.payment_transaction_id = payment_response.transaction_id

        if payment_response.status == PaymentStatus.COMPLETED:
            order.status = OrderStatus.PAID
        elif payment_response.status == PaymentStatus.FAILED:
            order.status = OrderStatus.PENDING
            # Restore stock if payment failed
            for item in order.items:
                product = self.db.query(Product).filter(Product.id == item.product_id).first()
                if product:
                    product.stock_quantity += item.quantity

        self.db.commit()
        self.db.refresh(order)

        if payment_response.status == PaymentStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment failed: {payment_response.message}"
            )

        return self._order_to_response(order)

    def get_user_orders(self, user_id: int, skip: int = 0, limit: int = 10) -> List[OrderSummary]:
        """
        Get user's orders.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List[OrderSummary]: List of user's orders
        """
        orders = self.db.query(Order).filter(
            Order.user_id == user_id
        ).order_by(Order.created_at.desc()).offset(skip).limit(limit).all()

        return [self._order_to_summary(order) for order in orders]

    def get_order(self, user_id: int, order_id: int) -> OrderResponse:
        """
        Get specific order for user.

        Args:
            user_id: User ID
            order_id: Order ID

        Returns:
            OrderResponse: Order details

        Raises:
            HTTPException: If order not found
        """
        order = self._get_user_order(user_id, order_id)
        return self._order_to_response(order)

    def update_order_status(self, order_id: int, update_data: OrderUpdate) -> OrderResponse:
        """
        Update order status (admin only).

        Args:
            order_id: Order ID
            update_data: Update data

        Returns:
            OrderResponse: Updated order

        Raises:
            HTTPException: If order not found or invalid status transition
        """
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )

        # Validate status transitions
        if update_data.status:
            if not self._validate_status_transition(order.status, update_data.status):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status transition from {order.status} to {update_data.status}"
                )
            order.status = update_data.status

            # Update timestamps
            if update_data.status == OrderStatus.SHIPPED:
                order.shipped_at = datetime.utcnow()
            elif update_data.status == OrderStatus.DELIVERED:
                order.delivered_at = datetime.utcnow()

        # Update other fields
        if update_data.payment_status:
            order.payment_status = update_data.payment_status
        if update_data.shipping_address:
            order.shipping_address = update_data.shipping_address
        if update_data.billing_address is not None:
            order.billing_address = update_data.billing_address
        if update_data.phone is not None:
            order.phone = update_data.phone
        if update_data.notes is not None:
            order.notes = update_data.notes
        if update_data.payment_transaction_id is not None:
            order.payment_transaction_id = update_data.payment_transaction_id

        self.db.commit()
        self.db.refresh(order)
        return self._order_to_response(order)

    def cancel_order(self, user_id: int, order_id: int) -> OrderResponse:
        """
        Cancel order.

        Args:
            user_id: User ID
            order_id: Order ID

        Returns:
            OrderResponse: Cancelled order

        Raises:
            HTTPException: If order not found or cannot be cancelled
        """
        order = self._get_user_order(user_id, order_id)

        if not order.can_be_cancelled():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order cannot be cancelled"
            )

        # Restore stock
        for item in order.items:
            product = self.db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                product.stock_quantity += item.quantity

        order.status = OrderStatus.CANCELLED
        self.db.commit()
        self.db.refresh(order)

        return self._order_to_response(order)

    def get_all_orders(self, skip: int = 0, limit: int = 10) -> List[OrderSummary]:
        """
        Get all orders (admin only).

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List[OrderSummary]: List of all orders
        """
        orders = self.db.query(Order).order_by(
            Order.created_at.desc()
        ).offset(skip).limit(limit).all()

        return [self._order_to_summary(order) for order in orders]

    def _get_user_order(self, user_id: int, order_id: int) -> Order:
        """
        Get order for specific user.

        Args:
            user_id: User ID
            order_id: Order ID

        Returns:
            Order: Order model

        Raises:
            HTTPException: If order not found
        """
        order = self.db.query(Order).filter(
            Order.id == order_id,
            Order.user_id == user_id
        ).first()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )

        return order

    def _generate_order_number(self) -> str:
        """
        Generate unique order number.

        Returns:
            str: Order number
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        unique_id = uuid.uuid4().hex[:8].upper()
        return f"ORD-{timestamp}-{unique_id}"

    def _validate_status_transition(self, current_status: OrderStatus, new_status: OrderStatus) -> bool:
        """
        Validate order status transition.

        Args:
            current_status: Current order status
            new_status: New order status

        Returns:
            bool: True if transition is valid
        """
        valid_transitions = {
            OrderStatus.PENDING: [OrderStatus.PAID, OrderStatus.CANCELLED],
            OrderStatus.PAID: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
            OrderStatus.SHIPPED: [OrderStatus.DELIVERED],
            OrderStatus.DELIVERED: [],
            OrderStatus.CANCELLED: []
        }

        return new_status in valid_transitions.get(current_status, [])

    def _order_to_response(self, order: Order) -> OrderResponse:
        """
        Convert order model to response schema.

        Args:
            order: Order model

        Returns:
            OrderResponse: Order response schema
        """
        items = []
        for item in order.items:
            items.append(OrderItemResponse(
                id=item.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
                line_total=item.line_total,
                product_name=item.product_name,
                product_sku=item.product_sku,
                created_at=item.created_at
            ))

        return OrderResponse(
            id=order.id,
            order_number=order.order_number,
            status=order.status,
            payment_status=order.payment_status,
            subtotal=order.subtotal,
            tax_amount=order.tax_amount,
            shipping_amount=order.shipping_amount,
            discount_amount=order.discount_amount,
            total_amount=order.total_amount,
            shipping_address=order.shipping_address,
            billing_address=order.billing_address,
            phone=order.phone,
            notes=order.notes,
            payment_method=order.payment_method,
            payment_transaction_id=order.payment_transaction_id,
            items_count=order.items_count,
            items=items,
            created_at=order.created_at,
            updated_at=order.updated_at,
            shipped_at=order.shipped_at,
            delivered_at=order.delivered_at
        )

    def _order_to_summary(self, order: Order) -> OrderSummary:
        """
        Convert order model to summary schema.

        Args:
            order: Order model

        Returns:
            OrderSummary: Order summary schema
        """
        return OrderSummary(
            id=order.id,
            order_number=order.order_number,
            status=order.status,
            payment_status=order.payment_status,
            total_amount=order.total_amount,
            items_count=order.items_count,
            created_at=order.created_at
        )