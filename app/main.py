"""
Main FastAPI application module.
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import create_tables
from app.logging_config import LoggingMiddleware, configure_logging, get_logger
from app.monitoring import metrics_collector
from app.rate_limiting import limiter, rate_limit_exceeded_handler
from app.routers.auth import router as auth_router
from app.routers.cart import router as cart_router
from app.routers.categories import router as categories_router
from app.routers.monitoring import router as monitoring_router
from app.routers.orders import router as orders_router
from app.routers.products import router as products_router

# Configure logging
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Application starting up")
    create_tables()
    logger.info("Database tables created")

    yield

    # Shutdown
    logger.info("Application shutting down")


# Create FastAPI instance
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Professional E-commerce API built with FastAPI - Production Ready",
    debug=settings.debug,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
    contact={
        "name": "E-commerce API Support",
        "email": "support@ecommerce-api.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    tags_metadata=[
        {
            "name": "Authentication",
            "description": "User authentication and authorization endpoints. Handle user registration, login, and token management.",
        },
        {
            "name": "products",
            "description": "Product catalog management. CRUD operations for products with advanced filtering and search capabilities.",
        },
        {
            "name": "categories",
            "description": "Product category management. Organize products into hierarchical categories.",
        },
        {
            "name": "cart",
            "description": "Shopping cart functionality. Manage user shopping carts and cart items.",
        },
        {
            "name": "orders",
            "description": "Order management system. Handle order creation, tracking, and status updates.",
        },
        {
            "name": "monitoring",
            "description": "System monitoring and health check endpoints. Monitor application performance and status.",
        },
    ],
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Configure CORS for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)


# Add metrics middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to collect metrics."""
    start_time = time.time()

    # Process request
    try:
        response = await call_next(request)
        metrics_collector.increment_request_count()

        # Record response time
        process_time = time.time() - start_time
        metrics_collector.add_response_time(process_time)

        # Add metrics headers
        response.headers["X-Process-Time"] = str(process_time)

        return response
    except Exception as e:
        metrics_collector.increment_error_count()
        raise


# Include routers
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(categories_router, prefix=settings.api_v1_prefix)
app.include_router(products_router, prefix=settings.api_v1_prefix)
app.include_router(cart_router, prefix=settings.api_v1_prefix)
app.include_router(orders_router, prefix=settings.api_v1_prefix)
app.include_router(monitoring_router, prefix=settings.api_v1_prefix)


@app.get("/")
@limiter.limit("200/minute")
async def root(request: Request):
    """
    Root endpoint with rate limiting.

    Returns:
        dict: Welcome message with API features
    """
    logger.info("root_endpoint_accessed")
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.version,
        "status": "active",
        "features": {
            "logging": "structured",
            "rate_limiting": "enabled",
            "monitoring": "enabled",
            "cors": "configured",
            "email_notifications": "simulated",
        },
        "status_info": "Production Ready",
    }


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting application server")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_config=None,  # Use our custom logging configuration
    )
