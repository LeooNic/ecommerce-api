"""
Product CRUD service.
"""

from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.category import Category
from app.models.product import Product
from app.schemas.product import (
    ProductCreate,
    ProductFilters,
    ProductList,
    ProductUpdate,
    StockUpdate,
)


class ProductService:
    """
    Service class for Product CRUD operations.
    """

    @staticmethod
    def create_product(db: Session, product_data: ProductCreate) -> Product:
        """
        Create a new product.

        Args:
            db: Database session
            product_data: Product creation data

        Returns:
            Product: Created product instance

        Raises:
            HTTPException: If product with same SKU or slug already exists, or category not found
        """
        # Check if product with same SKU or slug exists
        existing = (
            db.query(Product)
            .filter(
                or_(Product.sku == product_data.sku, Product.slug == product_data.slug)
            )
            .first()
        )

        if existing:
            if existing.sku == product_data.sku:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Product with this SKU already exists",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Product with this slug already exists",
                )

        # Validate category exists if provided
        if product_data.category_id:
            category = (
                db.query(Category)
                .filter(Category.id == product_data.category_id)
                .first()
            )
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found"
                )

        # Create new product
        db_product = Product(**product_data.model_dump())
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        return db_product

    @staticmethod
    def get_product(db: Session, product_id: int) -> Optional[Product]:
        """
        Get product by ID with category relationship.

        Args:
            db: Database session
            product_id: Product ID

        Returns:
            Optional[Product]: Product instance or None
        """
        return (
            db.query(Product)
            .options(joinedload(Product.category))
            .filter(Product.id == product_id)
            .first()
        )

    @staticmethod
    def get_product_by_slug(db: Session, slug: str) -> Optional[Product]:
        """
        Get product by slug with category relationship.

        Args:
            db: Database session
            slug: Product slug

        Returns:
            Optional[Product]: Product instance or None
        """
        return (
            db.query(Product)
            .options(joinedload(Product.category))
            .filter(Product.slug == slug)
            .first()
        )

    @staticmethod
    def get_product_by_sku(db: Session, sku: str) -> Optional[Product]:
        """
        Get product by SKU with category relationship.

        Args:
            db: Database session
            sku: Product SKU

        Returns:
            Optional[Product]: Product instance or None
        """
        return (
            db.query(Product)
            .options(joinedload(Product.category))
            .filter(Product.sku == sku)
            .first()
        )

    @staticmethod
    def get_products(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[ProductFilters] = None,
    ) -> ProductList:
        """
        Get paginated list of products with filtering.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Product filtering options

        Returns:
            ProductList: Paginated product list
        """
        query = db.query(Product).options(joinedload(Product.category))

        if filters:
            # Filter by active status
            if filters.is_active is not None:
                query = query.filter(Product.is_active == filters.is_active)

            # Filter by category
            if filters.category_id:
                query = query.filter(Product.category_id == filters.category_id)

            # Filter by price range
            if filters.min_price is not None:
                query = query.filter(Product.price >= filters.min_price)
            if filters.max_price is not None:
                query = query.filter(Product.price <= filters.max_price)

            # Filter by stock availability
            if filters.in_stock is not None:
                if filters.in_stock:
                    query = query.filter(Product.stock_quantity > 0)
                else:
                    query = query.filter(Product.stock_quantity == 0)

            # Filter by featured status
            if filters.is_featured is not None:
                query = query.filter(Product.is_featured == filters.is_featured)

            # Apply search filter
            if filters.search:
                search_term = f"%{filters.search}%"
                query = query.filter(
                    or_(
                        Product.name.ilike(search_term),
                        Product.description.ilike(search_term),
                        Product.sku.ilike(search_term),
                    )
                )

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        products = (
            query.order_by(Product.is_featured.desc(), Product.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        # Calculate pagination info
        page = (skip // limit) + 1 if limit > 0 else 1
        pages = (total + limit - 1) // limit if limit > 0 else 1

        return ProductList(
            items=products, total=total, page=page, size=limit, pages=pages
        )

    @staticmethod
    def update_product(
        db: Session, product_id: int, product_data: ProductUpdate
    ) -> Optional[Product]:
        """
        Update a product.

        Args:
            db: Database session
            product_id: Product ID
            product_data: Product update data

        Returns:
            Optional[Product]: Updated product instance

        Raises:
            HTTPException: If product not found, duplicate SKU/slug, or category not found
        """
        db_product = ProductService.get_product(db, product_id)
        if not db_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
            )

        update_data = product_data.model_dump(exclude_unset=True)

        # Check for duplicates if SKU or slug is being updated
        if "sku" in update_data or "slug" in update_data:
            query_filters = []
            if "sku" in update_data:
                query_filters.append(Product.sku == update_data["sku"])
            if "slug" in update_data:
                query_filters.append(Product.slug == update_data["slug"])

            existing = (
                db.query(Product)
                .filter(or_(*query_filters), Product.id != product_id)
                .first()
            )

            if existing:
                if "sku" in update_data and existing.sku == update_data["sku"]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Product with this SKU already exists",
                    )
                if "slug" in update_data and existing.slug == update_data["slug"]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Product with this slug already exists",
                    )

        # Validate category exists if being updated
        if "category_id" in update_data and update_data["category_id"]:
            category = (
                db.query(Category)
                .filter(Category.id == update_data["category_id"])
                .first()
            )
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found"
                )

        # Update product
        for field, value in update_data.items():
            setattr(db_product, field, value)

        db.commit()
        db.refresh(db_product)
        return db_product

    @staticmethod
    def update_stock(
        db: Session, product_id: int, stock_data: StockUpdate
    ) -> Optional[Product]:
        """
        Update product stock quantity.

        Args:
            db: Database session
            product_id: Product ID
            stock_data: Stock update data

        Returns:
            Optional[Product]: Updated product instance

        Raises:
            HTTPException: If product not found
        """
        db_product = ProductService.get_product(db, product_id)
        if not db_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
            )

        # Update stock
        db_product.stock_quantity = stock_data.stock_quantity
        if stock_data.low_stock_threshold is not None:
            db_product.low_stock_threshold = stock_data.low_stock_threshold

        db.commit()
        db.refresh(db_product)
        return db_product

    @staticmethod
    def delete_product(db: Session, product_id: int) -> bool:
        """
        Delete a product.

        Args:
            db: Database session
            product_id: Product ID

        Returns:
            bool: True if deleted successfully

        Raises:
            HTTPException: If product not found
        """
        db_product = ProductService.get_product(db, product_id)
        if not db_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
            )

        db.delete(db_product)
        db.commit()
        return True

    @staticmethod
    def get_featured_products(db: Session, limit: int = 10) -> List[Product]:
        """
        Get featured products.

        Args:
            db: Database session
            limit: Maximum number of products to return

        Returns:
            List[Product]: List of featured products
        """
        return (
            db.query(Product)
            .options(joinedload(Product.category))
            .filter(and_(Product.is_featured == True, Product.is_active == True))
            .order_by(Product.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_low_stock_products(db: Session, limit: int = 50) -> List[Product]:
        """
        Get products with low stock.

        Args:
            db: Database session
            limit: Maximum number of products to return

        Returns:
            List[Product]: List of low stock products
        """
        return (
            db.query(Product)
            .options(joinedload(Product.category))
            .filter(
                and_(
                    Product.is_active == True,
                    Product.stock_quantity <= Product.low_stock_threshold,
                )
            )
            .order_by(Product.stock_quantity.asc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def search_products(
        db: Session, search_term: str, limit: int = 20
    ) -> List[Product]:
        """
        Search products by name, description, or SKU.

        Args:
            db: Database session
            search_term: Search term
            limit: Maximum number of products to return

        Returns:
            List[Product]: List of matching products
        """
        search_filter = f"%{search_term}%"
        return (
            db.query(Product)
            .options(joinedload(Product.category))
            .filter(
                and_(
                    Product.is_active == True,
                    or_(
                        Product.name.ilike(search_filter),
                        Product.description.ilike(search_filter),
                        Product.sku.ilike(search_filter),
                    ),
                )
            )
            .order_by(Product.name)
            .limit(limit)
            .all()
        )
