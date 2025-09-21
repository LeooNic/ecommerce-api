"""
Category model definition.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.product import Product


class Category(Base):
    """
    Category model for product categorization.
    """

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    slug = Column(String(120), unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    products = relationship("Product", back_populates="category", lazy="dynamic")

    def __repr__(self) -> str:
        """
        String representation of Category model.

        Returns:
            str: Category representation
        """
        return f"<Category(id={self.id}, name={self.name}, slug={self.slug})>"

    @property
    def products_count(self) -> int:
        """
        Get count of products in this category.

        Returns:
            int: Number of products in category
        """
        return self.products.count() if hasattr(self, 'products') else 0