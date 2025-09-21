"""
Order and OrderItem model definitions.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, List

from sqlalchemy import (
    DECIMAL,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.user import User


class OrderStatus(str, Enum):
    """
    Order status enumeration.
    """

    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    """
    Payment status enumeration.
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class Order(Base):
    """
    Order model for e-commerce transactions.
    """

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, index=True, nullable=False)
    status = Column(String(20), default=OrderStatus.PENDING, nullable=False)
    payment_status = Column(String(20), default=PaymentStatus.PENDING, nullable=False)

    # Totals
    subtotal = Column(DECIMAL(10, 2), nullable=False)
    tax_amount = Column(DECIMAL(10, 2), default=0, nullable=False)
    shipping_amount = Column(DECIMAL(10, 2), default=0, nullable=False)
    discount_amount = Column(DECIMAL(10, 2), default=0, nullable=False)
    total_amount = Column(DECIMAL(10, 2), nullable=False)

    # Customer information
    shipping_address = Column(Text, nullable=False)
    billing_address = Column(Text, nullable=True)
    phone = Column(String(20), nullable=True)

    # Additional information
    notes = Column(Text, nullable=True)
    payment_method = Column(String(50), nullable=True)
    payment_transaction_id = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    shipped_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)

    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    user = relationship("User", back_populates="orders")
    items = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """
        String representation of Order model.

        Returns:
            str: Order representation
        """
        return f"<Order(id={self.id}, order_number={self.order_number}, status={self.status}, total={self.total_amount})>"

    @property
    def items_count(self) -> int:
        """
        Get total number of items in the order.

        Returns:
            int: Total quantity of all items
        """
        return sum(item.quantity for item in self.items)

    def can_be_cancelled(self) -> bool:
        """
        Check if order can be cancelled.

        Returns:
            bool: True if order can be cancelled
        """
        return self.status in [OrderStatus.PENDING, OrderStatus.PAID]

    def can_be_shipped(self) -> bool:
        """
        Check if order can be shipped.

        Returns:
            bool: True if order can be shipped
        """
        return (
            self.status == OrderStatus.PAID
            and self.payment_status == PaymentStatus.COMPLETED
        )

    def can_be_delivered(self) -> bool:
        """
        Check if order can be marked as delivered.

        Returns:
            bool: True if order can be delivered
        """
        return self.status == OrderStatus.SHIPPED


class OrderItem(Base):
    """
    Order item model for individual products in an order.
    """

    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(DECIMAL(10, 2), nullable=False)
    total_price = Column(DECIMAL(10, 2), nullable=False)

    # Product information at time of order (for historical accuracy)
    product_name = Column(String(200), nullable=False)
    product_sku = Column(String(100), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Foreign Keys
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product")

    def __repr__(self) -> str:
        """
        String representation of OrderItem model.

        Returns:
            str: OrderItem representation
        """
        return f"<OrderItem(id={self.id}, product={self.product_name}, quantity={self.quantity}, price={self.unit_price})>"

    @property
    def line_total(self) -> Decimal:
        """
        Calculate line total (quantity * unit_price).

        Returns:
            Decimal: Line total amount
        """
        return Decimal(str(self.quantity)) * self.unit_price
