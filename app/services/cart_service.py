"""
Cart service for managing shopping cart operations.
"""

from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.models.user import User
from app.schemas.cart import (
    CartResponse,
    CartItemResponse,
    AddToCartRequest,
    UpdateCartItemRequest,
    CartSummary
)


class CartService:
    """
    Service class for cart operations.
    """

    def __init__(self, db: Session):
        """
        Initialize cart service.

        Args:
            db: Database session
        """
        self.db = db

    def get_or_create_cart(self, user_id: int) -> Cart:
        """
        Get existing cart or create new one for user.

        Args:
            user_id: User ID

        Returns:
            Cart: User's cart
        """
        cart = self.db.query(Cart).filter(Cart.user_id == user_id).first()
        if not cart:
            cart = Cart(user_id=user_id)
            self.db.add(cart)
            self.db.commit()
            self.db.refresh(cart)
        return cart

    def get_cart(self, user_id: int) -> Optional[Cart]:
        """
        Get user's cart.

        Args:
            user_id: User ID

        Returns:
            Optional[Cart]: User's cart or None
        """
        return self.db.query(Cart).filter(Cart.user_id == user_id).first()

    def add_to_cart(self, user_id: int, request: AddToCartRequest) -> CartResponse:
        """
        Add product to cart.

        Args:
            user_id: User ID
            request: Add to cart request

        Returns:
            CartResponse: Updated cart

        Raises:
            HTTPException: If product not found or insufficient stock
        """
        # Validate product exists and is active
        product = self.db.query(Product).filter(
            Product.id == request.product_id,
            Product.is_active == True
        ).first()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found or inactive"
            )

        # Check stock availability
        if not product.can_order(request.quantity):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock. Available: {product.stock_quantity}"
            )

        # Get or create cart
        cart = self.get_or_create_cart(user_id)

        # Check if item already exists in cart
        existing_item = self.db.query(CartItem).filter(
            CartItem.cart_id == cart.id,
            CartItem.product_id == request.product_id
        ).first()

        if existing_item:
            # Update quantity
            new_quantity = existing_item.quantity + request.quantity
            if not product.can_order(new_quantity):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot add {request.quantity} more items. Total would be {new_quantity}, but only {product.stock_quantity} available"
                )
            existing_item.quantity = new_quantity
            existing_item.unit_price = product.price
        else:
            # Create new cart item
            cart_item = CartItem(
                cart_id=cart.id,
                product_id=request.product_id,
                quantity=request.quantity,
                unit_price=product.price
            )
            self.db.add(cart_item)

        self.db.commit()
        self.db.refresh(cart)
        return self._cart_to_response(cart)

    def remove_from_cart(self, user_id: int, product_id: int) -> CartResponse:
        """
        Remove product from cart.

        Args:
            user_id: User ID
            product_id: Product ID

        Returns:
            CartResponse: Updated cart

        Raises:
            HTTPException: If cart or item not found
        """
        cart = self.get_cart(user_id)
        if not cart:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart not found"
            )

        cart_item = self.db.query(CartItem).filter(
            CartItem.cart_id == cart.id,
            CartItem.product_id == product_id
        ).first()

        if not cart_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found in cart"
            )

        self.db.delete(cart_item)
        self.db.commit()
        self.db.refresh(cart)
        return self._cart_to_response(cart)

    def update_cart_item(self, user_id: int, product_id: int, request: UpdateCartItemRequest) -> CartResponse:
        """
        Update cart item quantity.

        Args:
            user_id: User ID
            product_id: Product ID
            request: Update request

        Returns:
            CartResponse: Updated cart

        Raises:
            HTTPException: If cart, item, or product not found, or insufficient stock
        """
        cart = self.get_cart(user_id)
        if not cart:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart not found"
            )

        cart_item = self.db.query(CartItem).filter(
            CartItem.cart_id == cart.id,
            CartItem.product_id == product_id
        ).first()

        if not cart_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found in cart"
            )

        # Validate product and stock
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product or not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found or inactive"
            )

        if not product.can_order(request.quantity):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock. Available: {product.stock_quantity}"
            )

        cart_item.quantity = request.quantity
        cart_item.unit_price = product.price
        self.db.commit()
        self.db.refresh(cart)
        return self._cart_to_response(cart)

    def clear_cart(self, user_id: int) -> CartResponse:
        """
        Clear all items from cart.

        Args:
            user_id: User ID

        Returns:
            CartResponse: Empty cart

        Raises:
            HTTPException: If cart not found
        """
        cart = self.get_cart(user_id)
        if not cart:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart not found"
            )

        # Delete all cart items
        self.db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
        self.db.commit()
        self.db.refresh(cart)
        return self._cart_to_response(cart)

    def get_cart_summary(self, user_id: int) -> CartSummary:
        """
        Get cart summary.

        Args:
            user_id: User ID

        Returns:
            CartSummary: Cart summary

        Raises:
            HTTPException: If cart not found
        """
        cart = self.get_cart(user_id)
        if not cart:
            return CartSummary(
                total_items=0,
                total_amount=Decimal('0.00'),
                items_count=0
            )

        return CartSummary(
            total_items=cart.total_items,
            total_amount=cart.total_amount,
            items_count=len(cart.items)
        )

    def _cart_to_response(self, cart: Cart) -> CartResponse:
        """
        Convert cart model to response schema.

        Args:
            cart: Cart model

        Returns:
            CartResponse: Cart response schema
        """
        items = []
        for item in cart.items:
            items.append(CartItemResponse(
                id=item.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
                product_name=item.product.name,
                product_sku=item.product.sku,
                created_at=item.created_at,
                updated_at=item.updated_at
            ))

        return CartResponse(
            id=cart.id,
            user_id=cart.user_id,
            total_items=cart.total_items,
            total_amount=cart.total_amount,
            is_empty=cart.is_empty,
            items=items,
            created_at=cart.created_at,
            updated_at=cart.updated_at
        )