"""
Monitoring and health check endpoints for the application.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.logging_config import get_logger
from app.monitoring import health_checker, metrics_collector
from app.rate_limiting import RateLimitConfig, check_rate_limit_status, limiter

logger = get_logger(__name__)

router = APIRouter(tags=["monitoring"])


@router.get("/health")
@limiter.limit(RateLimitConfig.HEALTH_LIMIT)
async def health_check(request: Request):
    """
    Basic health check endpoint.

    Returns:
        Basic health status
    """
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.version,
        "environment": "development" if settings.debug else "production",
    }


@router.get("/health/detailed")
@limiter.limit(RateLimitConfig.HEALTH_LIMIT)
async def detailed_health_check(request: Request, db: Session = Depends(get_db)):
    """
    Comprehensive health check endpoint.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        Detailed health check results
    """
    try:
        health_data = await health_checker.get_comprehensive_health(db)

        # Log health check
        logger.info(
            "health_check_performed",
            status=health_data["status"],
            timestamp=health_data["timestamp"],
        )

        return health_data
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Health check failed",
        )


@router.get("/metrics")
@limiter.limit(RateLimitConfig.HEALTH_LIMIT)
async def get_metrics(request: Request):
    """
    Get application metrics.

    Args:
        request: FastAPI request object

    Returns:
        Application metrics data
    """
    if not settings.enable_metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Metrics endpoint is disabled"
        )

    try:
        metrics_data = metrics_collector.get_metrics()

        logger.info("metrics_requested", timestamp=metrics_data["timestamp"])

        return metrics_data
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics",
        )


@router.get("/rate-limit/status")
@limiter.limit(RateLimitConfig.API_LIMIT)
async def get_rate_limit_status(request: Request):
    """
    Get current rate limit status for the client.

    Args:
        request: FastAPI request object

    Returns:
        Rate limit status information
    """
    try:
        status_data = await check_rate_limit_status(request)
        return status_data
    except Exception as e:
        logger.error(f"Failed to get rate limit status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve rate limit status",
        )
