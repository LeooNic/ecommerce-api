"""
Categories router with CRUD endpoints.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.category import (
    CategoryCreate,
    CategoryList,
    CategoryResponse,
    CategoryUpdate,
)
from app.services.category import CategoryService
from app.utils.auth import get_current_active_user, get_current_admin_user

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Create a new category.

    Requires admin privileges.

    Args:
        category_data: Category creation data
        db: Database session
        current_user: Current authenticated admin user

    Returns:
        CategoryResponse: Created category

    Raises:
        HTTPException: If category with same name or slug already exists
    """
    return CategoryService.create_category(db, category_data)


@router.get("/", response_model=CategoryList)
async def get_categories(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of records to return"),
    active_only: bool = Query(True, description="Return only active categories"),
    search: Optional[str] = Query(
        None, description="Search term for category name or description"
    ),
    db: Session = Depends(get_db),
):
    """
    Get paginated list of categories.

    Public endpoint - no authentication required.

    Args:
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        active_only: Whether to return only active categories
        search: Search term for filtering categories
        db: Database session

    Returns:
        CategoryList: Paginated list of categories
    """
    return CategoryService.get_categories(
        db=db, skip=skip, limit=limit, active_only=active_only, search=search
    )


@router.get("/active", response_model=list[CategoryResponse])
async def get_active_categories(db: Session = Depends(get_db)):
    """
    Get all active categories.

    Public endpoint for dropdown lists and category selection.

    Args:
        db: Database session

    Returns:
        List[CategoryResponse]: List of active categories
    """
    categories = CategoryService.get_active_categories(db)
    return categories


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: int, db: Session = Depends(get_db)):
    """
    Get a category by ID.

    Public endpoint - no authentication required.

    Args:
        category_id: Category ID
        db: Database session

    Returns:
        CategoryResponse: Category details

    Raises:
        HTTPException: If category not found
    """
    category = CategoryService.get_category(db, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    return category


@router.get("/slug/{slug}", response_model=CategoryResponse)
async def get_category_by_slug(slug: str, db: Session = Depends(get_db)):
    """
    Get a category by slug.

    Public endpoint - no authentication required.

    Args:
        slug: Category slug
        db: Database session

    Returns:
        CategoryResponse: Category details

    Raises:
        HTTPException: If category not found
    """
    category = CategoryService.get_category_by_slug(db, slug)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Update a category.

    Requires admin privileges.

    Args:
        category_id: Category ID
        category_data: Category update data
        db: Database session
        current_user: Current authenticated admin user

    Returns:
        CategoryResponse: Updated category

    Raises:
        HTTPException: If category not found or duplicate name/slug
    """
    return CategoryService.update_category(db, category_id, category_data)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Delete a category.

    Requires admin privileges.

    Args:
        category_id: Category ID
        db: Database session
        current_user: Current authenticated admin user

    Raises:
        HTTPException: If category not found or has associated products
    """
    CategoryService.delete_category(db, category_id)
    return None
