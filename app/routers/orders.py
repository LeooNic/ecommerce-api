"""
Order management API endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.order import (
    OrderResponse,
    OrderSummary,
    CheckoutRequest,
    OrderUpdate
)
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.utils.auth import get_current_active_user, get_current_admin_user
from app.email_service import email_service
from app.logging_config import get_logger
from app.rate_limiting import limiter, RateLimitConfig

logger = get_logger(__name__)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/checkout", response_model=OrderResponse)
@limiter.limit(RateLimitConfig.WRITE_LIMIT)
async def checkout(
    request: Request,
    checkout_request: CheckoutRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create order from cart (checkout).

    Args:
        checkout_request: Checkout details

    Returns:
        OrderResponse: Created order

    Raises:
        HTTPException: If cart is empty or validation fails
    """
    order_service = OrderService(db)
    order = order_service.create_order_from_cart(current_user.id, checkout_request)

    # Send order confirmation email
    try:
        order_data = {
            "id": order.id,
            "created_at": order.created_at,
            "total_amount": order.total_amount,
            "status": order.status,
            "items": [
                {
                    "product_name": item.product.name,
                    "quantity": item.quantity,
                    "price": item.price
                }
                for item in order.items
            ]
        }

        await email_service.send_order_confirmation(
            user_email=current_user.email,
            user_name=f"{current_user.first_name} {current_user.last_name}",
            order_data=order_data
        )
        logger.info(f"Order confirmation email sent to {current_user.email} for order {order.id}")
    except Exception as e:
        logger.error(f"Failed to send order confirmation email: {e}")

    return order


@router.post("/{order_id}/pay", response_model=OrderResponse)
async def pay_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Process payment for order.

    Args:
        order_id: Order ID to pay

    Returns:
        OrderResponse: Updated order with payment status

    Raises:
        HTTPException: If order not found or cannot be paid
    """
    order_service = OrderService(db)
    return order_service.process_payment(current_user.id, order_id)


@router.get("/", response_model=List[OrderSummary])
async def get_user_orders(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of records to return"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's orders.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List[OrderSummary]: List of user's orders
    """
    order_service = OrderService(db)
    return order_service.get_user_orders(current_user.id, skip, limit)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get specific order details.

    Args:
        order_id: Order ID

    Returns:
        OrderResponse: Order details

    Raises:
        HTTPException: If order not found
    """
    order_service = OrderService(db)
    return order_service.get_order(current_user.id, order_id)


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Cancel order.

    Args:
        order_id: Order ID to cancel

    Returns:
        OrderResponse: Cancelled order

    Raises:
        HTTPException: If order not found or cannot be cancelled
    """
    order_service = OrderService(db)
    return order_service.cancel_order(current_user.id, order_id)


# Admin endpoints
@router.get("/admin/all", response_model=List[OrderSummary])
async def get_all_orders(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of records to return"),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get all orders (admin only).

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List[OrderSummary]: List of all orders
    """
    order_service = OrderService(db)
    return order_service.get_all_orders(skip, limit)


@router.put("/admin/{order_id}", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    update_data: OrderUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Update order status (admin only).

    Args:
        order_id: Order ID to update
        update_data: Update data

    Returns:
        OrderResponse: Updated order

    Raises:
        HTTPException: If order not found or invalid status transition
    """
    order_service = OrderService(db)
    return order_service.update_order_status(order_id, update_data)


@router.get("/admin/{order_id}", response_model=OrderResponse)
async def get_order_admin(
    order_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get order details (admin only).

    Args:
        order_id: Order ID

    Returns:
        OrderResponse: Order details

    Raises:
        HTTPException: If order not found
    """
    from app.models.order import Order
    order_service = OrderService(db)
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    return order_service._order_to_response(order)


# Payment information endpoints
@router.get("/payment/methods")
async def get_payment_methods():
    """
    Get supported payment methods.

    Returns:
        Dict: Supported payment methods with details
    """
    payment_service = PaymentService()
    return {
        "supported_methods": payment_service.get_supported_methods(),
        "message": "Supported payment methods for checkout"
    }