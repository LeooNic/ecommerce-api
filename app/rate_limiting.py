"""
Rate limiting implementation using Redis and slowapi.
"""

import time
from typing import Optional, Union

import redis
from fastapi import HTTPException, Request, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

# Redis connection for rate limiting
redis_client: Optional[redis.Redis] = None

try:
    redis_client = redis.Redis(
        host=getattr(settings, "redis_host", "localhost"),
        port=getattr(settings, "redis_port", 6379),
        db=getattr(settings, "redis_db", 0),
        decode_responses=True,
    )
    # Test connection
    redis_client.ping()
    logger.info("Redis connection established for rate limiting")
except Exception as e:
    logger.warning(f"Redis not available, using in-memory rate limiting: {e}")
    redis_client = None


def get_rate_limit_key(request: Request) -> str:
    """
    Generate rate limit key based on user or IP address.

    Args:
        request: FastAPI request object

    Returns:
        Rate limit key string
    """
    # Try to get user ID from request state (set by auth middleware)
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"

    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"


# Create limiter instance
if redis_client:
    limiter = Limiter(key_func=get_rate_limit_key, storage_uri="redis://localhost:6379")
else:
    limiter = Limiter(key_func=get_rate_limit_key, storage_uri="memory://")


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom rate limit exceeded handler.

    Args:
        request: FastAPI request object
        exc: RateLimitExceeded exception

    Returns:
        HTTPException with appropriate message
    """
    retry_after = getattr(exc, "retry_after", 60)  # Default to 60 seconds

    logger.warning(
        "rate_limit_exceeded",
        key=get_rate_limit_key(request),
        path=request.url.path,
        retry_after=retry_after,
    )

    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "Rate limit exceeded",
            "message": f"Too many requests. Try again in {retry_after} seconds.",
            "retry_after": retry_after,
        },
    )


class RateLimitConfig:
    """
    Configuration for different rate limits based on endpoint types.
    """

    # Authentication endpoints - more restrictive
    AUTH_LIMIT = "5/minute"

    # General API endpoints
    API_LIMIT = "100/minute"

    # Search and read operations - less restrictive
    READ_LIMIT = "200/minute"

    # Write operations - moderately restrictive
    WRITE_LIMIT = "50/minute"

    # Admin operations - very restrictive
    ADMIN_LIMIT = "10/minute"

    # Health checks - very permissive
    HEALTH_LIMIT = "1000/minute"


def get_user_rate_limit_info(request: Request, limit_key: str) -> dict:
    """
    Get current rate limit information for a user/IP.

    Args:
        request: FastAPI request object
        limit_key: Rate limit key

    Returns:
        Dictionary with rate limit information
    """
    if not redis_client:
        return {"available": True, "message": "Rate limiting not fully configured"}

    try:
        key = get_rate_limit_key(request)
        current_time = int(time.time())
        window_size = 60  # 1 minute window

        # Get current count in the time window
        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(f"rate_limit:{key}", 0, current_time - window_size)
        pipe.zcard(f"rate_limit:{key}")
        pipe.expire(f"rate_limit:{key}", window_size)
        results = pipe.execute()

        current_count = results[1]

        # Parse limit (e.g., "100/minute" -> 100)
        limit_value = int(limit_key.split("/")[0]) if "/" in limit_key else 100

        return {
            "limit": limit_value,
            "remaining": max(0, limit_value - current_count),
            "reset_time": current_time + window_size,
            "current_count": current_count,
        }
    except Exception as e:
        logger.error(f"Error getting rate limit info: {e}")
        return {"available": True, "message": "Rate limit info unavailable"}


async def check_rate_limit_status(request: Request) -> dict:
    """
    Check rate limit status for the current request.

    Args:
        request: FastAPI request object

    Returns:
        Rate limit status information
    """
    key = get_rate_limit_key(request)
    path = request.url.path

    # Determine appropriate limit based on path
    if "/auth/" in path:
        limit = RateLimitConfig.AUTH_LIMIT
    elif "/admin/" in path:
        limit = RateLimitConfig.ADMIN_LIMIT
    elif "/health" in path or "/metrics" in path:
        limit = RateLimitConfig.HEALTH_LIMIT
    elif request.method in ["GET", "HEAD"]:
        limit = RateLimitConfig.READ_LIMIT
    elif request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        limit = RateLimitConfig.WRITE_LIMIT
    else:
        limit = RateLimitConfig.API_LIMIT

    return get_user_rate_limit_info(request, limit)
