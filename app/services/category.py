"""
Category CRUD service.
"""

from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryList, CategoryUpdate


class CategoryService:
    """
    Service class for Category CRUD operations.
    """

    @staticmethod
    def create_category(db: Session, category_data: CategoryCreate) -> Category:
        """
        Create a new category.

        Args:
            db: Database session
            category_data: Category creation data

        Returns:
            Category: Created category instance

        Raises:
            HTTPException: If category with same name or slug already exists
        """
        # Check if category with same name or slug exists
        existing = (
            db.query(Category)
            .filter(
                or_(
                    Category.name == category_data.name,
                    Category.slug == category_data.slug,
                )
            )
            .first()
        )

        if existing:
            if existing.name == category_data.name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Category with this name already exists",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Category with this slug already exists",
                )

        # Create new category
        db_category = Category(**category_data.model_dump())
        db.add(db_category)
        db.commit()
        db.refresh(db_category)
        return db_category

    @staticmethod
    def get_category(db: Session, category_id: int) -> Optional[Category]:
        """
        Get category by ID.

        Args:
            db: Database session
            category_id: Category ID

        Returns:
            Optional[Category]: Category instance or None
        """
        return db.query(Category).filter(Category.id == category_id).first()

    @staticmethod
    def get_category_by_slug(db: Session, slug: str) -> Optional[Category]:
        """
        Get category by slug.

        Args:
            db: Database session
            slug: Category slug

        Returns:
            Optional[Category]: Category instance or None
        """
        return db.query(Category).filter(Category.slug == slug).first()

    @staticmethod
    def get_categories(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
        search: Optional[str] = None,
    ) -> CategoryList:
        """
        Get paginated list of categories.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            active_only: Whether to return only active categories
            search: Search term for category name or description

        Returns:
            CategoryList: Paginated category list
        """
        query = db.query(Category)

        # Filter by active status
        if active_only:
            query = query.filter(Category.is_active == True)

        # Apply search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Category.name.ilike(search_term),
                    Category.description.ilike(search_term),
                )
            )

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        categories = query.order_by(Category.name).offset(skip).limit(limit).all()

        # Calculate pagination info
        page = (skip // limit) + 1 if limit > 0 else 1
        pages = (total + limit - 1) // limit if limit > 0 else 1

        return CategoryList(
            items=categories, total=total, page=page, size=limit, pages=pages
        )

    @staticmethod
    def update_category(
        db: Session, category_id: int, category_data: CategoryUpdate
    ) -> Optional[Category]:
        """
        Update a category.

        Args:
            db: Database session
            category_id: Category ID
            category_data: Category update data

        Returns:
            Optional[Category]: Updated category instance

        Raises:
            HTTPException: If category not found or duplicate name/slug
        """
        db_category = CategoryService.get_category(db, category_id)
        if not db_category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
            )

        # Check for duplicates if name or slug is being updated
        update_data = category_data.model_dump(exclude_unset=True)

        if "name" in update_data or "slug" in update_data:
            query_filters = []
            if "name" in update_data:
                query_filters.append(Category.name == update_data["name"])
            if "slug" in update_data:
                query_filters.append(Category.slug == update_data["slug"])

            existing = (
                db.query(Category)
                .filter(or_(*query_filters), Category.id != category_id)
                .first()
            )

            if existing:
                if "name" in update_data and existing.name == update_data["name"]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Category with this name already exists",
                    )
                if "slug" in update_data and existing.slug == update_data["slug"]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Category with this slug already exists",
                    )

        # Update category
        for field, value in update_data.items():
            setattr(db_category, field, value)

        db.commit()
        db.refresh(db_category)
        return db_category

    @staticmethod
    def delete_category(db: Session, category_id: int) -> bool:
        """
        Delete a category.

        Args:
            db: Database session
            category_id: Category ID

        Returns:
            bool: True if deleted successfully

        Raises:
            HTTPException: If category not found or has associated products
        """
        db_category = CategoryService.get_category(db, category_id)
        if not db_category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
            )

        # Check if category has products
        if db_category.products.count() > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete category with associated products",
            )

        db.delete(db_category)
        db.commit()
        return True

    @staticmethod
    def get_active_categories(db: Session) -> List[Category]:
        """
        Get all active categories.

        Args:
            db: Database session

        Returns:
            List[Category]: List of active categories
        """
        return (
            db.query(Category)
            .filter(Category.is_active == True)
            .order_by(Category.name)
            .all()
        )
