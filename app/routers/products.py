"""
Products router with CRUD endpoints and advanced features.
"""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.product import (
    ProductCreate,
    ProductFilters,
    ProductList,
    ProductListItem,
    ProductResponse,
    ProductUpdate,
    StockUpdate,
)
from app.services.product import ProductService
from app.utils.auth import get_current_active_user, get_current_admin_user

router = APIRouter(prefix="/products", tags=["products"])


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
    description="Create a new product in the catalog. Requires admin privileges.",
    response_description="The created product with generated ID and timestamps",
    responses={
        201: {
            "description": "Product created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Wireless Headphones",
                        "description": "Premium noise-cancelling wireless headphones",
                        "price": 299.99,
                        "sku": "WH-001",
                        "category_id": 1,
                        "stock_quantity": 50,
                        "is_active": True,
                        "is_featured": False,
                        "slug": "wireless-headphones",
                        "created_at": "2024-01-01T12:00:00.000Z",
                        "updated_at": "2024-01-01T12:00:00.000Z",
                    }
                }
            },
        },
        400: {
            "description": "Validation error or duplicate SKU/slug",
            "content": {
                "application/json": {
                    "example": {"detail": "Product with this SKU already exists"}
                }
            },
        },
        403: {
            "description": "Admin privileges required",
            "content": {
                "application/json": {"example": {"detail": "Admin privileges required"}}
            },
        },
    },
)
async def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Create a new product in the catalog.

    Only admin users can create products. The SKU and slug must be unique.
    The slug is automatically generated from the product name if not provided.

    **Required fields:**
    - **name**: Product name (max 200 characters)
    - **price**: Product price (must be positive)
    - **sku**: Stock Keeping Unit (unique identifier)
    - **category_id**: Valid category ID

    **Optional fields:**
    - **description**: Product description
    - **stock_quantity**: Initial stock (defaults to 0)
    - **is_active**: Product visibility (defaults to True)
    - **is_featured**: Featured status (defaults to False)
    """
    return ProductService.create_product(db, product_data)


@router.get(
    "/",
    response_model=ProductList,
    summary="Get products with filtering and pagination",
    description="Retrieve a paginated list of products with advanced filtering options",
    response_description="Paginated list of products with metadata",
    responses={
        200: {
            "description": "Products retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": 1,
                                "name": "Wireless Headphones",
                                "description": "Premium noise-cancelling wireless headphones",
                                "price": 299.99,
                                "sku": "WH-001",
                                "category_id": 1,
                                "stock_quantity": 50,
                                "is_active": True,
                                "is_featured": True,
                                "slug": "wireless-headphones",
                            }
                        ],
                        "total": 1,
                        "skip": 0,
                        "limit": 100,
                        "has_next": False,
                    }
                }
            },
        }
    },
)
async def get_products(
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(
        100, ge=1, le=100, description="Maximum number of records to return"
    ),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    min_price: Optional[Decimal] = Query(
        None, ge=0, description="Minimum price filter"
    ),
    max_price: Optional[Decimal] = Query(
        None, gt=0, description="Maximum price filter"
    ),
    in_stock: Optional[bool] = Query(
        None,
        description="Filter by stock availability (true=in stock, false=out of stock)",
    ),
    is_featured: Optional[bool] = Query(None, description="Filter by featured status"),
    is_active: Optional[bool] = Query(
        True, description="Filter by active status (defaults to true)"
    ),
    search: Optional[str] = Query(
        None, description="Search term for product name, description, or SKU"
    ),
    db: Session = Depends(get_db),
):
    """
    Get paginated list of products with comprehensive filtering.

    This is a public endpoint that doesn't require authentication. It supports
    advanced filtering, searching, and pagination for browsing the product catalog.

    **Pagination:**
    - Use `skip` and `limit` parameters for pagination
    - Maximum limit is 100 products per request
    - Response includes pagination metadata

    **Filtering Options:**
    - **category_id**: Filter by specific category
    - **min_price/max_price**: Price range filtering
    - **in_stock**: Filter by stock availability
    - **is_featured**: Filter featured products
    - **is_active**: Filter active products (defaults to true)
    - **search**: Search in name, description, and SKU

    **Example Usage:**
    - Get first 10 products: `?limit=10`
    - Get electronics under $500: `?category_id=1&max_price=500`
    - Search for "wireless": `?search=wireless`
    - Get featured products in stock: `?is_featured=true&in_stock=true`
    """
    filters = ProductFilters(
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock,
        is_featured=is_featured,
        is_active=is_active,
        search=search,
    )

    return ProductService.get_products(db=db, skip=skip, limit=limit, filters=filters)


@router.get("/featured", response_model=list[ProductResponse])
async def get_featured_products(
    limit: int = Query(
        10, ge=1, le=50, description="Number of featured products to return"
    ),
    db: Session = Depends(get_db),
):
    """
    Get featured products.

    Public endpoint for homepage and promotional displays.

    Args:
        limit: Maximum number of products to return
        db: Database session

    Returns:
        List[ProductResponse]: List of featured products
    """
    products = ProductService.get_featured_products(db, limit)
    return products


@router.get("/low-stock", response_model=list[ProductResponse])
async def get_low_stock_products(
    limit: int = Query(
        50, ge=1, le=100, description="Number of low stock products to return"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Get products with low stock.

    Requires admin privileges - for inventory management.

    Args:
        limit: Maximum number of products to return
        db: Database session
        current_user: Current authenticated admin user

    Returns:
        List[ProductResponse]: List of low stock products
    """
    products = ProductService.get_low_stock_products(db, limit)
    return products


@router.get("/search", response_model=list[ProductResponse])
async def search_products(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(
        20, ge=1, le=50, description="Number of search results to return"
    ),
    db: Session = Depends(get_db),
):
    """
    Search products by name, description, or SKU.

    Public endpoint for product search functionality.

    Args:
        q: Search query string
        limit: Maximum number of results to return
        db: Database session

    Returns:
        List[ProductResponse]: List of matching products
    """
    products = ProductService.search_products(db, q, limit)
    return products


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: Session = Depends(get_db)):
    """
    Get a product by ID.

    Public endpoint - no authentication required.

    Args:
        product_id: Product ID
        db: Database session

    Returns:
        ProductResponse: Product details

    Raises:
        HTTPException: If product not found
    """
    product = ProductService.get_product(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    return product


@router.get("/slug/{slug}", response_model=ProductResponse)
async def get_product_by_slug(slug: str, db: Session = Depends(get_db)):
    """
    Get a product by slug.

    Public endpoint - no authentication required.

    Args:
        slug: Product slug
        db: Database session

    Returns:
        ProductResponse: Product details

    Raises:
        HTTPException: If product not found
    """
    product = ProductService.get_product_by_slug(db, slug)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    return product


@router.get("/sku/{sku}", response_model=ProductResponse)
async def get_product_by_sku(
    sku: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Get a product by SKU.

    Requires admin privileges - for internal inventory management.

    Args:
        sku: Product SKU
        db: Database session
        current_user: Current authenticated admin user

    Returns:
        ProductResponse: Product details

    Raises:
        HTTPException: If product not found
    """
    product = ProductService.get_product_by_sku(db, sku)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    return product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Update a product.

    Requires admin privileges.

    Args:
        product_id: Product ID
        product_data: Product update data
        db: Database session
        current_user: Current authenticated admin user

    Returns:
        ProductResponse: Updated product

    Raises:
        HTTPException: If product not found, duplicate SKU/slug, or category not found
    """
    return ProductService.update_product(db, product_id, product_data)


@router.patch("/{product_id}/stock", response_model=ProductResponse)
async def update_product_stock(
    product_id: int,
    stock_data: StockUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Update product stock quantity.

    Requires admin privileges.

    Args:
        product_id: Product ID
        stock_data: Stock update data
        db: Database session
        current_user: Current authenticated admin user

    Returns:
        ProductResponse: Updated product

    Raises:
        HTTPException: If product not found
    """
    return ProductService.update_stock(db, product_id, stock_data)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Delete a product.

    Requires admin privileges.

    Args:
        product_id: Product ID
        db: Database session
        current_user: Current authenticated admin user

    Raises:
        HTTPException: If product not found
    """
    ProductService.delete_product(db, product_id)
    return None
