"""
Product model definition.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

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
    from app.models.category import Category


class Product(Base):
    """
    Product model for e-commerce catalog.
    """

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), index=True, nullable=False)
    description = Column(Text, nullable=True)
    slug = Column(String(220), unique=True, index=True, nullable=False)
    sku = Column(String(100), unique=True, index=True, nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)
    compare_price = Column(DECIMAL(10, 2), nullable=True)
    cost_price = Column(DECIMAL(10, 2), nullable=True)
    stock_quantity = Column(Integer, default=0, nullable=False)
    low_stock_threshold = Column(Integer, default=10, nullable=False)
    weight = Column(DECIMAL(8, 3), nullable=True)
    dimensions = Column(String(100), nullable=True)  # formato: "LxWxH cm"
    is_active = Column(Boolean, default=True, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)
    requires_shipping = Column(Boolean, default=True, nullable=False)
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Foreign Keys
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    # Relationships
    category = relationship("Category", back_populates="products")

    def __repr__(self) -> str:
        """
        String representation of Product model.

        Returns:
            str: Product representation
        """
        return f"<Product(id={self.id}, name={self.name}, sku={self.sku}, price={self.price})>"

    @property
    def is_on_sale(self) -> bool:
        """
        Check if product is on sale (compare_price > price).

        Returns:
            bool: True if product has a compare price higher than current price
        """
        return bool(self.compare_price and self.compare_price > self.price)

    @property
    def discount_percentage(self) -> Optional[float]:
        """
        Calculate discount percentage if product is on sale.

        Returns:
            Optional[float]: Discount percentage or None
        """
        if not self.is_on_sale:
            return None

        discount = float(self.compare_price - self.price)
        percentage = (discount / float(self.compare_price)) * 100
        return round(percentage, 2)

    @property
    def is_in_stock(self) -> bool:
        """
        Check if product is in stock.

        Returns:
            bool: True if stock quantity is greater than 0
        """
        return self.stock_quantity > 0

    @property
    def is_low_stock(self) -> bool:
        """
        Check if product has low stock.

        Returns:
            bool: True if stock is below threshold
        """
        return self.stock_quantity <= self.low_stock_threshold

    def can_order(self, quantity: int = 1) -> bool:
        """
        Check if a specific quantity can be ordered.

        Args:
            quantity: Quantity to check

        Returns:
            bool: True if quantity is available
        """
        return self.is_active and self.stock_quantity >= quantity
