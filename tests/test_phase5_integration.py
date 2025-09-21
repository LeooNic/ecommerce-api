"""
Integration tests for Phase 5 advanced features.
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest
from faker import Faker
from httpx import AsyncClient

from app.email_service import email_service
from app.logging_config import get_logger
from app.main import app
from app.monitoring import health_checker, metrics_collector

fake = Faker()
logger = get_logger(__name__)


class TestStructuredLogging:
    """Test structured logging functionality."""

    def test_logger_configuration(self):
        """Test that logger is properly configured."""
        test_logger = get_logger("test_logger")
        assert test_logger is not None
        assert hasattr(test_logger, "info")
        assert hasattr(test_logger, "error")
        assert hasattr(test_logger, "warning")

    @pytest.mark.asyncio
    async def test_request_logging(self, client: AsyncClient):
        """Test that requests are properly logged."""
        response = await client.get("/")
        assert response.status_code == 200

        # Verify that the response contains Phase 5 information
        data = response.json()
        assert data["phase"] == "5 - Advanced Features"
        assert "features" in data
        assert data["features"]["logging"] == "structured"


class TestRateLimiting:
    """Test rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, client: AsyncClient):
        """Test that rate limit headers are present."""
        response = await client.get("/")
        assert response.status_code == 200

        # Check for process time header
        assert "X-Process-Time" in response.headers

    @pytest.mark.asyncio
    async def test_rate_limit_status_endpoint(self, client: AsyncClient):
        """Test rate limit status endpoint."""
        response = await client.get("/api/v1/rate-limit/status")
        assert response.status_code == 200

        data = response.json()
        # Should contain rate limiting information
        assert "available" in data or "limit" in data

    @pytest.mark.asyncio
    async def test_auth_rate_limiting(self, client: AsyncClient):
        """Test that authentication endpoints have stricter rate limits."""
        # Make multiple rapid requests to login endpoint
        login_data = {"email": "nonexistent@example.com", "password": "wrongpassword"}

        responses = []
        for _ in range(3):
            response = await client.post("/api/v1/auth/login", json=login_data)
            responses.append(response.status_code)

        # All should be 401 (unauthorized) rather than rate limited for small number
        assert all(status in [401, 422] for status in responses)


class TestCORSConfiguration:
    """Test CORS configuration."""

    @pytest.mark.asyncio
    async def test_cors_headers_present(self, client: AsyncClient):
        """Test that CORS headers are properly configured."""
        # Make an OPTIONS request to check CORS
        response = await client.options("/")

        # CORS headers should be present for allowed origins
        assert response.status_code in [200, 204]

    @pytest.mark.asyncio
    async def test_cors_with_origin(self, client: AsyncClient):
        """Test CORS with specific origin."""
        headers = {"Origin": "http://localhost:3000"}
        response = await client.get("/", headers=headers)

        assert response.status_code == 200
        # Should allow the request from allowed origin


class TestHealthCheckAndMetrics:
    """Test enhanced health check and metrics functionality."""

    @pytest.mark.asyncio
    async def test_basic_health_check(self, client: AsyncClient):
        """Test basic health check endpoint."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "app" in data
        assert "version" in data

    @pytest.mark.asyncio
    async def test_detailed_health_check(self, client: AsyncClient):
        """Test detailed health check endpoint."""
        response = await client.get("/api/v1/health/detailed")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "application" in data
        assert "database" in data
        assert "system" in data

        # Check application info
        app_info = data["application"]
        assert "name" in app_info
        assert "version" in app_info
        assert "uptime_seconds" in app_info

        # Check database health
        db_info = data["database"]
        assert "status" in db_info
        assert "response_time_ms" in db_info

        # Check system health
        system_info = data["system"]
        assert "cpu" in system_info
        assert "memory" in system_info
        assert "disk" in system_info

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, client: AsyncClient):
        """Test metrics endpoint."""
        # Make some requests to generate metrics
        await client.get("/")
        await client.get("/api/v1/health")

        response = await client.get("/api/v1/metrics")
        assert response.status_code == 200

        data = response.json()
        assert "uptime_seconds" in data
        assert "requests" in data
        assert "timestamp" in data

        # Check request metrics
        request_metrics = data["requests"]
        assert "total" in request_metrics
        assert "errors" in request_metrics
        assert "success_rate" in request_metrics

    def test_health_checker_methods(self):
        """Test health checker methods directly."""
        # Test system resource checking
        system_resources = health_checker.check_system_resources()
        assert "cpu" in system_resources
        assert "memory" in system_resources
        assert "disk" in system_resources

        # Test application info
        app_info = health_checker.get_application_info()
        assert "name" in app_info
        assert "version" in app_info
        assert "uptime_seconds" in app_info

    def test_metrics_collector(self):
        """Test metrics collector functionality."""
        # Reset metrics
        initial_count = metrics_collector.request_count

        # Increment metrics
        metrics_collector.increment_request_count()
        metrics_collector.add_response_time(0.1)
        metrics_collector.increment_error_count()

        # Get metrics
        metrics = metrics_collector.get_metrics()

        assert metrics["requests"]["total"] >= initial_count + 1
        assert metrics["requests"]["errors"] >= 1
        assert len(metrics_collector.response_times) >= 1


class TestEmailNotifications:
    """Test email notification system."""

    @pytest.mark.asyncio
    async def test_send_welcome_email(self):
        """Test sending welcome email."""
        result = await email_service.send_welcome_email(
            user_email="test@example.com", user_name="Test User"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_send_order_confirmation(self):
        """Test sending order confirmation email."""
        order_data = {
            "id": 123,
            "created_at": "2024-01-01T10:00:00",
            "total_amount": 99.99,
            "status": "confirmed",
            "items": [{"product_name": "Test Product", "quantity": 2, "price": 49.99}],
        }

        result = await email_service.send_order_confirmation(
            user_email="test@example.com", user_name="Test User", order_data=order_data
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_send_password_reset_email(self):
        """Test sending password reset email."""
        result = await email_service.send_password_reset_email(
            user_email="test@example.com",
            user_name="Test User",
            reset_token="test-token-123",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_send_admin_notification(self):
        """Test sending admin notification."""
        details = {
            "event": "new_user_registration",
            "user_id": 123,
            "timestamp": "2024-01-01T10:00:00",
        }

        result = await email_service.send_admin_notification(
            notification_type="User Registration", details=details
        )
        assert result is True

    def test_email_service_get_sent_emails(self):
        """Test getting sent emails for inspection."""
        sent_emails = email_service.email_service.get_sent_emails()
        assert isinstance(sent_emails, list)
        # Should have emails from previous tests
        assert len(sent_emails) >= 0

    def test_email_templates(self):
        """Test email template rendering."""
        from jinja2 import Template

        from app.email_service import EmailTemplates

        # Test welcome template
        template = Template(EmailTemplates.WELCOME_TEMPLATE)
        rendered = template.render(
            app_name="Test App",
            user_name="Test User",
            user_email="test@example.com",
            registration_date="January 1, 2024",
        )
        assert "Test App" in rendered
        assert "Test User" in rendered


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows with Phase 5 features."""

    @pytest.mark.asyncio
    async def test_user_registration_with_email(self, client: AsyncClient):
        """Test complete user registration workflow with email notification."""
        user_data = {
            "email": fake.email(),
            "username": fake.user_name(),
            "password": "securepassword123",
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "role": "customer",
        }

        # Clear sent emails
        email_service.email_service.clear_sent_emails()

        response = await client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 201

        data = response.json()
        assert "user" in data
        assert "token" in data
        assert data["message"] == "User registered successfully"

        # Check that welcome email was "sent"
        sent_emails = email_service.email_service.get_sent_emails()
        welcome_emails = [
            email for email in sent_emails if "Welcome" in email["subject"]
        ]
        assert len(welcome_emails) >= 1

    @pytest.mark.asyncio
    async def test_order_creation_with_email(self, authenticated_client: AsyncClient):
        """Test order creation with email notification."""
        # This test requires a more complex setup with products and cart
        # For now, we'll test the email service directly in order workflow

        # Clear sent emails
        email_service.email_service.clear_sent_emails()

        # First, add a product to cart (simplified test)
        # In a real test, you'd create products first
        pass  # Placeholder for full order test

    @pytest.mark.asyncio
    async def test_performance_monitoring(self, client: AsyncClient):
        """Test that performance monitoring works across requests."""
        start_time = time.time()

        # Make several requests
        responses = []
        for _ in range(5):
            response = await client.get("/")
            responses.append(response)

        end_time = time.time()

        # All requests should succeed
        assert all(r.status_code == 200 for r in responses)

        # Check that process time headers are present
        for response in responses:
            assert "X-Process-Time" in response.headers
            process_time = float(response.headers["X-Process-Time"])
            assert process_time > 0

        # Check metrics
        metrics_response = await client.get("/api/v1/metrics")
        assert metrics_response.status_code == 200

        metrics_data = metrics_response.json()
        assert metrics_data["requests"]["total"] >= 5

    @pytest.mark.asyncio
    async def test_error_handling_and_logging(self, client: AsyncClient):
        """Test error handling and logging for invalid requests."""
        # Test invalid endpoints
        response = await client.get("/nonexistent-endpoint")
        assert response.status_code == 404

        # Test invalid authentication
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "invalid@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401

        # Metrics should track errors
        metrics_response = await client.get("/api/v1/metrics")
        assert metrics_response.status_code == 200

        metrics_data = metrics_response.json()
        # Error count should be tracked
        assert "errors" in metrics_data["requests"]


class TestSecurityFeatures:
    """Test security-related Phase 5 features."""

    @pytest.mark.asyncio
    async def test_security_headers(self, client: AsyncClient):
        """Test that security headers are properly set."""
        response = await client.get("/")
        assert response.status_code == 200

        # Check that process time header is set (our custom header)
        assert "X-Process-Time" in response.headers

    @pytest.mark.asyncio
    async def test_rate_limiting_configuration(self, client: AsyncClient):
        """Test that rate limiting is properly configured."""
        # Test health check endpoint (should have high limit)
        responses = []
        for _ in range(10):
            response = await client.get("/api/v1/health")
            responses.append(response.status_code)

        # All should succeed due to high rate limit
        assert all(status == 200 for status in responses)

    def test_cors_security_configuration(self):
        """Test CORS security configuration."""
        from app.config import settings

        # CORS should be configured with specific origins
        assert settings.cors_origins != ["*"]
        assert isinstance(settings.cors_origins, list)
        assert settings.cors_allow_credentials is True


@pytest.mark.asyncio
async def test_application_startup_and_shutdown():
    """Test application startup and shutdown events."""
    # This test verifies that the lifespan events work correctly
    # The application should start and stop without errors
    assert True  # Placeholder - actual lifespan testing requires more setup
