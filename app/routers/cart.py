"""
Cart management API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.cart import (
    CartResponse,
    AddToCartRequest,
    UpdateCartItemRequest,
    CartSummary
)
from app.services.cart_service import CartService
from app.utils.auth import get_current_active_user

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("/", response_model=CartResponse)
async def get_cart(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's cart.

    Returns:
        CartResponse: User's cart with items
    """
    cart_service = CartService(db)
    cart = cart_service.get_cart(current_user.id)

    if not cart:
        # Return empty cart if no cart exists
        return CartResponse(
            id=0,
            user_id=current_user.id,
            total_items=0,
            total_amount=0,
            is_empty=True,
            items=[],
            created_at=None,
            updated_at=None
        )

    return cart_service._cart_to_response(cart)


@router.post("/add", response_model=CartResponse)
async def add_to_cart(
    request: AddToCartRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add product to cart.

    Args:
        request: Product and quantity to add

    Returns:
        CartResponse: Updated cart

    Raises:
        HTTPException: If product not found or insufficient stock
    """
    cart_service = CartService(db)
    return cart_service.add_to_cart(current_user.id, request)


@router.put("/items/{product_id}", response_model=CartResponse)
async def update_cart_item(
    product_id: int,
    request: UpdateCartItemRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update cart item quantity.

    Args:
        product_id: Product ID to update
        request: New quantity

    Returns:
        CartResponse: Updated cart

    Raises:
        HTTPException: If item not found or insufficient stock
    """
    cart_service = CartService(db)
    return cart_service.update_cart_item(current_user.id, product_id, request)


@router.delete("/items/{product_id}", response_model=CartResponse)
async def remove_from_cart(
    product_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Remove product from cart.

    Args:
        product_id: Product ID to remove

    Returns:
        CartResponse: Updated cart

    Raises:
        HTTPException: If item not found
    """
    cart_service = CartService(db)
    return cart_service.remove_from_cart(current_user.id, product_id)


@router.delete("/clear", response_model=CartResponse)
async def clear_cart(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Clear all items from cart.

    Returns:
        CartResponse: Empty cart
    """
    cart_service = CartService(db)
    return cart_service.clear_cart(current_user.id)


@router.get("/summary", response_model=CartSummary)
async def get_cart_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get cart summary with totals.

    Returns:
        CartSummary: Cart summary information
    """
    cart_service = CartService(db)
    return cart_service.get_cart_summary(current_user.id)