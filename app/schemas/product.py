"""
Product schemas for request/response serialization.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, validator

from app.schemas.category import CategoryResponse


class ProductBase(BaseModel):
    """
    Base product schema with common fields.
    """

    name: str = Field(..., min_length=1, max_length=200, description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    slug: str = Field(
        ..., min_length=1, max_length=220, description="URL-friendly product identifier"
    )
    sku: str = Field(
        ..., min_length=1, max_length=100, description="Stock Keeping Unit"
    )
    price: Decimal = Field(..., gt=0, description="Product price")
    compare_price: Optional[Decimal] = Field(
        None, description="Compare at price for discounts"
    )
    cost_price: Optional[Decimal] = Field(
        None, description="Cost price for profit calculations"
    )
    stock_quantity: int = Field(0, ge=0, description="Available stock quantity")
    low_stock_threshold: int = Field(
        10, ge=0, description="Low stock warning threshold"
    )
    weight: Optional[Decimal] = Field(None, description="Product weight in kg")
    dimensions: Optional[str] = Field(
        None, max_length=100, description="Product dimensions (LxWxH cm)"
    )
    is_active: bool = Field(True, description="Whether the product is active")
    is_featured: bool = Field(False, description="Whether the product is featured")
    requires_shipping: bool = Field(
        True, description="Whether the product requires shipping"
    )
    meta_title: Optional[str] = Field(
        None, max_length=255, description="SEO meta title"
    )
    meta_description: Optional[str] = Field(None, description="SEO meta description")
    category_id: Optional[int] = Field(None, description="Category ID")

    @validator("compare_price")
    def validate_compare_price(cls, v, values):
        """
        Validate that compare_price is greater than price if provided.
        """
        if v is not None and "price" in values and v <= values["price"]:
            raise ValueError("Compare price must be greater than regular price")
        return v

    @validator("cost_price")
    def validate_cost_price(cls, v, values):
        """
        Validate that cost_price is less than price if provided.
        """
        if v is not None and "price" in values and v >= values["price"]:
            raise ValueError("Cost price should be less than selling price")
        return v


class ProductCreate(ProductBase):
    """
    Schema for creating a new product.
    """

    pass


class ProductUpdate(BaseModel):
    """
    Schema for updating an existing product.
    """

    name: Optional[str] = Field(
        None, min_length=1, max_length=200, description="Product name"
    )
    description: Optional[str] = Field(None, description="Product description")
    slug: Optional[str] = Field(
        None,
        min_length=1,
        max_length=220,
        description="URL-friendly product identifier",
    )
    sku: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Stock Keeping Unit"
    )
    price: Optional[Decimal] = Field(None, gt=0, description="Product price")
    compare_price: Optional[Decimal] = Field(
        None, description="Compare at price for discounts"
    )
    cost_price: Optional[Decimal] = Field(
        None, description="Cost price for profit calculations"
    )
    stock_quantity: Optional[int] = Field(
        None, ge=0, description="Available stock quantity"
    )
    low_stock_threshold: Optional[int] = Field(
        None, ge=0, description="Low stock warning threshold"
    )
    weight: Optional[Decimal] = Field(None, description="Product weight in kg")
    dimensions: Optional[str] = Field(
        None, max_length=100, description="Product dimensions (LxWxH cm)"
    )
    is_active: Optional[bool] = Field(None, description="Whether the product is active")
    is_featured: Optional[bool] = Field(
        None, description="Whether the product is featured"
    )
    requires_shipping: Optional[bool] = Field(
        None, description="Whether the product requires shipping"
    )
    meta_title: Optional[str] = Field(
        None, max_length=255, description="SEO meta title"
    )
    meta_description: Optional[str] = Field(None, description="SEO meta description")
    category_id: Optional[int] = Field(None, description="Category ID")


class ProductResponse(ProductBase):
    """
    Schema for product response.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_on_sale: bool = Field(..., description="Whether the product is on sale")
    discount_percentage: Optional[float] = Field(
        None, description="Discount percentage if on sale"
    )
    is_in_stock: bool = Field(..., description="Whether the product is in stock")
    is_low_stock: bool = Field(..., description="Whether the product has low stock")
    category: Optional[CategoryResponse] = Field(None, description="Product category")
    created_at: datetime
    updated_at: datetime


class ProductListItem(BaseModel):
    """
    Schema for product list items (simplified response).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    sku: str
    price: Decimal
    compare_price: Optional[Decimal]
    stock_quantity: int
    is_active: bool
    is_featured: bool
    is_on_sale: bool
    is_in_stock: bool
    category: Optional[CategoryResponse]
    created_at: datetime


class ProductList(BaseModel):
    """
    Schema for paginated product list response.
    """

    items: List[ProductListItem]
    total: int = Field(..., description="Total number of products")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")


class ProductFilters(BaseModel):
    """
    Schema for product filtering parameters.
    """

    category_id: Optional[int] = Field(None, description="Filter by category ID")
    min_price: Optional[Decimal] = Field(None, ge=0, description="Minimum price filter")
    max_price: Optional[Decimal] = Field(None, gt=0, description="Maximum price filter")
    in_stock: Optional[bool] = Field(None, description="Filter by stock availability")
    is_featured: Optional[bool] = Field(None, description="Filter by featured status")
    is_active: Optional[bool] = Field(True, description="Filter by active status")
    search: Optional[str] = Field(
        None, min_length=1, max_length=200, description="Search term"
    )

    @validator("max_price")
    def validate_price_range(cls, v, values):
        """
        Validate that max_price is greater than min_price if both provided.
        """
        if v is not None and "min_price" in values and values["min_price"] is not None:
            if v <= values["min_price"]:
                raise ValueError("Maximum price must be greater than minimum price")
        return v


class StockUpdate(BaseModel):
    """
    Schema for updating product stock.
    """

    stock_quantity: int = Field(..., ge=0, description="New stock quantity")
    low_stock_threshold: Optional[int] = Field(
        None, ge=0, description="Low stock warning threshold"
    )
