"""
Performance tests for the FastAPI e-commerce application.
"""

import pytest
import asyncio
import time
from httpx import AsyncClient
from concurrent.futures import ThreadPoolExecutor
import statistics


class TestPerformance:
    """Performance tests for critical application endpoints."""

    @pytest.mark.asyncio
    async def test_root_endpoint_performance(self, client: AsyncClient):
        """Test root endpoint performance."""
        response_times = []

        for _ in range(20):
            start_time = time.time()
            response = await client.get("/")
            end_time = time.time()

            assert response.status_code == 200
            response_times.append(end_time - start_time)

        # Performance assertions
        avg_time = statistics.mean(response_times)
        max_time = max(response_times)

        assert avg_time < 0.1, f"Average response time too high: {avg_time:.3f}s"
        assert max_time < 0.2, f"Maximum response time too high: {max_time:.3f}s"

    @pytest.mark.asyncio
    async def test_health_check_performance(self, client: AsyncClient):
        """Test health check endpoint performance."""
        response_times = []

        for _ in range(10):
            start_time = time.time()
            response = await client.get("/api/v1/health")
            end_time = time.time()

            assert response.status_code == 200
            response_times.append(end_time - start_time)

        avg_time = statistics.mean(response_times)
        assert avg_time < 0.05, f"Health check too slow: {avg_time:.3f}s"

    @pytest.mark.asyncio
    async def test_detailed_health_check_performance(self, client: AsyncClient):
        """Test detailed health check performance."""
        response_times = []

        for _ in range(5):
            start_time = time.time()
            response = await client.get("/api/v1/health/detailed")
            end_time = time.time()

            assert response.status_code == 200
            response_times.append(end_time - start_time)

        avg_time = statistics.mean(response_times)
        assert avg_time < 0.2, f"Detailed health check too slow: {avg_time:.3f}s"

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client: AsyncClient):
        """Test application performance under concurrent load."""
        async def make_request():
            start_time = time.time()
            response = await client.get("/")
            end_time = time.time()
            return response.status_code, end_time - start_time

        # Create 20 concurrent requests
        tasks = [make_request() for _ in range(20)]
        results = await asyncio.gather(*tasks)

        # All requests should succeed
        status_codes = [result[0] for result in results]
        response_times = [result[1] for result in results]

        assert all(status == 200 for status in status_codes)

        # Performance under load
        avg_time = statistics.mean(response_times)
        max_time = max(response_times)

        assert avg_time < 0.3, f"Average response time under load too high: {avg_time:.3f}s"
        assert max_time < 0.5, f"Maximum response time under load too high: {max_time:.3f}s"

    @pytest.mark.asyncio
    async def test_rate_limiting_performance(self, client: AsyncClient):
        """Test rate limiting overhead."""
        # Test without rate limiting overhead (health endpoint with high limits)
        start_time = time.time()
        for _ in range(10):
            response = await client.get("/api/v1/health")
            assert response.status_code == 200
        end_time = time.time()

        total_time = end_time - start_time
        avg_per_request = total_time / 10

        # Rate limiting shouldn't add significant overhead
        assert avg_per_request < 0.1, f"Rate limiting overhead too high: {avg_per_request:.3f}s per request"

    @pytest.mark.asyncio
    async def test_metrics_collection_performance(self, client: AsyncClient):
        """Test metrics collection performance."""
        # Make some requests to generate metrics
        for _ in range(5):
            await client.get("/")

        # Test metrics endpoint performance
        start_time = time.time()
        response = await client.get("/api/v1/metrics")
        end_time = time.time()

        assert response.status_code == 200
        response_time = end_time - start_time

        assert response_time < 0.1, f"Metrics collection too slow: {response_time:.3f}s"

    @pytest.mark.asyncio
    async def test_logging_performance_impact(self, client: AsyncClient):
        """Test that logging doesn't significantly impact performance."""
        # This is more of a smoke test to ensure logging doesn't break performance
        response_times = []

        for _ in range(10):
            start_time = time.time()
            response = await client.get("/")
            end_time = time.time()

            assert response.status_code == 200
            response_times.append(end_time - start_time)

        avg_time = statistics.mean(response_times)
        # Logging should not add significant overhead
        assert avg_time < 0.15, f"Logging adds too much overhead: {avg_time:.3f}s"


class TestMemoryPerformance:
    """Test memory usage and efficiency."""

    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, client: AsyncClient):
        """Test that memory usage remains stable under load."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Make many requests
        for _ in range(50):
            response = await client.get("/")
            assert response.status_code == 200

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024, f"Memory usage increased too much: {memory_increase / 1024 / 1024:.2f}MB"

    def test_metrics_memory_efficiency(self):
        """Test that metrics collection doesn't cause memory leaks."""
        from app.monitoring import metrics_collector

        initial_response_times = len(metrics_collector.response_times)

        # Add many response times
        for i in range(2000):
            metrics_collector.add_response_time(0.1)

        # Should not exceed the limit (1000 measurements)
        assert len(metrics_collector.response_times) <= 1000

        # Should keep the most recent measurements
        assert len(metrics_collector.response_times) == 1000


class TestDatabasePerformance:
    """Test database-related performance."""

    @pytest.mark.asyncio
    async def test_database_health_check_performance(self, client: AsyncClient):
        """Test database health check performance."""
        response_times = []

        for _ in range(5):
            start_time = time.time()
            response = await client.get("/api/v1/health/detailed")
            end_time = time.time()

            assert response.status_code == 200
            data = response.json()
            assert data["database"]["status"] == "healthy"

            response_times.append(end_time - start_time)

        # Database health check should be reasonably fast
        avg_time = statistics.mean(response_times)
        assert avg_time < 0.3, f"Database health check too slow: {avg_time:.3f}s"

        # Check that database response time is tracked
        response = await client.get("/api/v1/health/detailed")
        data = response.json()
        db_response_time = data["database"]["response_time_ms"]
        assert db_response_time < 100, f"Database response time too high: {db_response_time}ms"


class TestEmailPerformance:
    """Test email service performance."""

    @pytest.mark.asyncio
    async def test_email_sending_performance(self):
        """Test email sending performance (simulated)."""
        from app.email_service import email_service

        start_time = time.time()

        # Send multiple emails concurrently
        tasks = []
        for i in range(10):
            task = email_service.send_welcome_email(
                user_email=f"test{i}@example.com",
                user_name=f"Test User {i}"
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        end_time = time.time()

        # All emails should be sent successfully
        assert all(results)

        total_time = end_time - start_time
        avg_per_email = total_time / 10

        # Email sending should be fast (since it's simulated)
        assert avg_per_email < 0.01, f"Email sending too slow: {avg_per_email:.3f}s per email"
        assert total_time < 0.1, f"Total email sending time too high: {total_time:.3f}s"


class TestStartupPerformance:
    """Test application startup performance."""

    def test_logger_initialization_performance(self):
        """Test logger initialization performance."""
        from app.logging_config import get_logger

        start_time = time.time()
        for i in range(100):
            logger = get_logger(f"test_logger_{i}")
        end_time = time.time()

        total_time = end_time - start_time
        assert total_time < 0.1, f"Logger initialization too slow: {total_time:.3f}s"

    def test_monitoring_initialization_performance(self):
        """Test monitoring system initialization performance."""
        from app.monitoring import HealthChecker, MetricsCollector

        start_time = time.time()

        # Initialize multiple instances
        for _ in range(10):
            health_checker = HealthChecker()
            metrics_collector = MetricsCollector()

        end_time = time.time()

        total_time = end_time - start_time
        assert total_time < 0.05, f"Monitoring initialization too slow: {total_time:.3f}s"


@pytest.mark.asyncio
async def test_overall_application_performance(client: AsyncClient):
    """Overall application performance test."""
    # Test a realistic user workflow
    start_time = time.time()

    # 1. Check health
    health_response = await client.get("/api/v1/health")
    assert health_response.status_code == 200

    # 2. Access root endpoint
    root_response = await client.get("/")
    assert root_response.status_code == 200

    # 3. Check metrics
    metrics_response = await client.get("/api/v1/metrics")
    assert metrics_response.status_code == 200

    # 4. Detailed health check
    detailed_health_response = await client.get("/api/v1/health/detailed")
    assert detailed_health_response.status_code == 200

    end_time = time.time()
    total_workflow_time = end_time - start_time

    # Complete workflow should be fast
    assert total_workflow_time < 0.5, f"Complete workflow too slow: {total_workflow_time:.3f}s"