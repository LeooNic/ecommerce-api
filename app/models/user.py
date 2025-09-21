"""
User model definition.
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from app.database import Base


class UserRole(str, Enum):
    """
    User roles enumeration.
    """
    ADMIN = "admin"
    CUSTOMER = "customer"


class User(Base):
    """
    User model for authentication and authorization.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default=UserRole.CUSTOMER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    orders = relationship("Order", back_populates="user")
    cart = relationship("Cart", back_populates="user", uselist=False)

    def __repr__(self) -> str:
        """
        String representation of User model.

        Returns:
            str: User representation
        """
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

    @property
    def full_name(self) -> str:
        """
        Get user's full name.

        Returns:
            str: Combined first and last name
        """
        return f"{self.first_name} {self.last_name}"

    def is_admin(self) -> bool:
        """
        Check if user has admin role.

        Returns:
            bool: True if user is admin
        """
        return self.role == UserRole.ADMIN