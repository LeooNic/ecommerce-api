"""
Cart-related Pydantic schemas.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class CartItemBase(BaseModel):
    """
    Base schema for cart item.
    """
    quantity: int = Field(gt=0, description="Quantity must be greater than 0")


class CartItemCreate(CartItemBase):
    """
    Schema for creating a cart item.
    """
    product_id: int = Field(gt=0, description="Product ID must be greater than 0")


class CartItemUpdate(BaseModel):
    """
    Schema for updating a cart item.
    """
    quantity: int = Field(gt=0, description="Quantity must be greater than 0")


class CartItemResponse(CartItemBase):
    """
    Schema for cart item response.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    unit_price: Decimal
    subtotal: Decimal
    product_name: str
    product_sku: str
    created_at: datetime
    updated_at: datetime


class CartBase(BaseModel):
    """
    Base schema for cart.
    """
    pass


class CartResponse(CartBase):
    """
    Schema for cart response.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    total_items: int
    total_amount: Decimal
    is_empty: bool
    items: List[CartItemResponse] = []
    created_at: datetime
    updated_at: datetime


class AddToCartRequest(BaseModel):
    """
    Schema for adding items to cart.
    """
    product_id: int = Field(gt=0, description="Product ID must be greater than 0")
    quantity: int = Field(gt=0, description="Quantity must be greater than 0")


class UpdateCartItemRequest(BaseModel):
    """
    Schema for updating cart item quantity.
    """
    quantity: int = Field(gt=0, description="Quantity must be greater than 0")


class CartSummary(BaseModel):
    """
    Schema for cart summary.
    """
    total_items: int
    total_amount: Decimal
    items_count: int