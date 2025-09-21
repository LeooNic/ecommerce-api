"""
Order-related Pydantic schemas.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderStatus, PaymentStatus


class OrderItemBase(BaseModel):
    """
    Base schema for order item.
    """

    quantity: int = Field(gt=0, description="Quantity must be greater than 0")
    unit_price: Decimal = Field(gt=0, description="Unit price must be greater than 0")


class OrderItemCreate(OrderItemBase):
    """
    Schema for creating an order item.
    """

    product_id: int = Field(gt=0, description="Product ID must be greater than 0")


class OrderItemResponse(OrderItemBase):
    """
    Schema for order item response.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    product_sku: str
    total_price: Decimal
    line_total: Decimal
    created_at: datetime


class OrderBase(BaseModel):
    """
    Base schema for order.
    """

    shipping_address: str = Field(
        min_length=10, description="Shipping address is required"
    )
    billing_address: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None


class OrderCreate(OrderBase):
    """
    Schema for creating an order.
    """

    payment_method: Optional[str] = Field(None, max_length=50)


class OrderUpdate(BaseModel):
    """
    Schema for updating an order.
    """

    status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None
    shipping_address: Optional[str] = Field(None, min_length=10)
    billing_address: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None
    payment_transaction_id: Optional[str] = Field(None, max_length=100)


class OrderResponse(OrderBase):
    """
    Schema for order response.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    status: OrderStatus
    payment_status: PaymentStatus
    subtotal: Decimal
    tax_amount: Decimal
    shipping_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    payment_method: Optional[str]
    payment_transaction_id: Optional[str]
    items_count: int
    items: List[OrderItemResponse] = []
    created_at: datetime
    updated_at: datetime
    shipped_at: Optional[datetime]
    delivered_at: Optional[datetime]


class OrderSummary(BaseModel):
    """
    Schema for order summary without items.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    status: OrderStatus
    payment_status: PaymentStatus
    total_amount: Decimal
    items_count: int
    created_at: datetime


class CheckoutRequest(OrderBase):
    """
    Schema for checkout request.
    """

    payment_method: str = Field(min_length=1, description="Payment method is required")


class PaymentRequest(BaseModel):
    """
    Schema for payment processing.
    """

    payment_method: str = Field(min_length=1, description="Payment method is required")
    amount: Decimal = Field(gt=0, description="Amount must be greater than 0")


class PaymentResponse(BaseModel):
    """
    Schema for payment response.
    """

    transaction_id: str
    status: PaymentStatus
    amount: Decimal
    message: str
