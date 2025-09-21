"""
Category schemas for request/response serialization.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CategoryBase(BaseModel):
    """
    Base category schema with common fields.
    """

    name: str = Field(..., min_length=1, max_length=100, description="Category name")
    description: Optional[str] = Field(None, description="Category description")
    slug: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="URL-friendly category identifier",
    )
    is_active: bool = Field(True, description="Whether the category is active")


class CategoryCreate(CategoryBase):
    """
    Schema for creating a new category.
    """

    pass


class CategoryUpdate(BaseModel):
    """
    Schema for updating an existing category.
    """

    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Category name"
    )
    description: Optional[str] = Field(None, description="Category description")
    slug: Optional[str] = Field(
        None,
        min_length=1,
        max_length=120,
        description="URL-friendly category identifier",
    )
    is_active: Optional[bool] = Field(
        None, description="Whether the category is active"
    )


class CategoryResponse(CategoryBase):
    """
    Schema for category response.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    products_count: int = Field(0, description="Number of products in this category")
    created_at: datetime
    updated_at: datetime


class CategoryWithProducts(CategoryResponse):
    """
    Schema for category response with product details.
    """

    pass  # This will be implemented when product relationships are needed


class CategoryList(BaseModel):
    """
    Schema for paginated category list response.
    """

    items: list[CategoryResponse]
    total: int = Field(..., description="Total number of categories")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")
