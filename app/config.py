"""
Application configuration module.
"""

import os
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings configuration.
    """

    # App settings
    app_name: str = "E-commerce API"
    version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"

    # Database settings
    database_url: str = "sqlite:///./ecommerce.db"

    # Security settings
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # API settings
    api_v1_prefix: str = "/api/v1"

    # Phase 5: Advanced features settings
    # Redis settings for rate limiting
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # CORS settings
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    cors_allow_credentials: bool = True

    # Email settings
    admin_email: str = "admin@example.com"
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@ecommerce-api.com"

    # Monitoring settings
    enable_metrics: bool = True
    metrics_path: str = "/metrics"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
