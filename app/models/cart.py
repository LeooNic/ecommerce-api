"""
Cart and CartItem model definitions.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DECIMAL, Column, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.user import User


class Cart(Base):
    """
    Shopping cart model for temporary storage before checkout.
    """

    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    user = relationship("User", back_populates="cart")
    items = relationship(
        "CartItem", back_populates="cart", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """
        String representation of Cart model.

        Returns:
            str: Cart representation
        """
        return f"<Cart(id={self.id}, user_id={self.user_id}, items_count={len(self.items)})>"

    @property
    def total_items(self) -> int:
        """
        Get total number of items in the cart.

        Returns:
            int: Total quantity of all items
        """
        return sum(item.quantity for item in self.items)

    @property
    def total_amount(self) -> Decimal:
        """
        Calculate total amount of all items in the cart.

        Returns:
            Decimal: Total cart amount
        """
        return sum(item.subtotal for item in self.items)

    @property
    def is_empty(self) -> bool:
        """
        Check if cart is empty.

        Returns:
            bool: True if cart has no items
        """
        return len(self.items) == 0


class CartItem(Base):
    """
    Cart item model for individual products in a shopping cart.
    """

    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(DECIMAL(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Foreign Keys
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    # Relationships
    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")

    def __repr__(self) -> str:
        """
        String representation of CartItem model.

        Returns:
            str: CartItem representation
        """
        return f"<CartItem(id={self.id}, product_id={self.product_id}, quantity={self.quantity})>"

    @property
    def subtotal(self) -> Decimal:
        """
        Calculate subtotal for this cart item.

        Returns:
            Decimal: Subtotal amount (quantity * unit_price)
        """
        return Decimal(str(self.quantity)) * self.unit_price
