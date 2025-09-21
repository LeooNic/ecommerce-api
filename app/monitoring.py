"""
Enhanced monitoring, health checks, and metrics for the application.
"""

import time
import psutil
from typing import Dict, Any, Optional
from sqlalchemy import text
from fastapi import Depends
from app.database import get_db
from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


class HealthChecker:
    """
    Comprehensive health checking functionality.
    """

    def __init__(self):
        self.start_time = time.time()

    async def check_database_health(self, db) -> Dict[str, Any]:
        """
        Check database connectivity and performance.

        Args:
            db: Database session

        Returns:
            Database health information
        """
        try:
            start_time = time.time()

            # Simple connectivity test
            result = db.execute(text("SELECT 1"))
            result.fetchone()

            # Performance test
            query_time = time.time() - start_time

            return {
                "status": "healthy",
                "response_time_ms": round(query_time * 1000, 2),
                "connection": "active"
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "connection": "failed"
            }

    def check_system_resources(self) -> Dict[str, Any]:
        """
        Check system resource usage.

        Returns:
            System resource information
        """
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()

            # Disk usage
            disk = psutil.disk_usage('/')

            return {
                "cpu": {
                    "usage_percent": cpu_percent,
                    "status": "healthy" if cpu_percent < 80 else "warning"
                },
                "memory": {
                    "total_mb": round(memory.total / (1024 * 1024), 2),
                    "available_mb": round(memory.available / (1024 * 1024), 2),
                    "usage_percent": memory.percent,
                    "status": "healthy" if memory.percent < 80 else "warning"
                },
                "disk": {
                    "total_gb": round(disk.total / (1024 * 1024 * 1024), 2),
                    "free_gb": round(disk.free / (1024 * 1024 * 1024), 2),
                    "usage_percent": round((disk.used / disk.total) * 100, 2),
                    "status": "healthy" if (disk.used / disk.total) < 0.8 else "warning"
                }
            }
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            return {
                "status": "error",
                "message": f"Unable to check system resources: {e}"
            }

    def get_application_info(self) -> Dict[str, Any]:
        """
        Get application runtime information.

        Returns:
            Application information
        """
        uptime_seconds = time.time() - self.start_time

        return {
            "name": settings.app_name,
            "version": settings.version,
            "uptime_seconds": round(uptime_seconds, 2),
            "uptime_human": self._format_uptime(uptime_seconds),
            "environment": "development" if settings.debug else "production",
            "api_prefix": settings.api_v1_prefix
        }

    def _format_uptime(self, seconds: float) -> str:
        """
        Format uptime in human-readable format.

        Args:
            seconds: Uptime in seconds

        Returns:
            Formatted uptime string
        """
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{secs}s")

        return " ".join(parts)

    async def get_comprehensive_health(self, db) -> Dict[str, Any]:
        """
        Get comprehensive health check information.

        Args:
            db: Database session

        Returns:
            Complete health check results
        """
        database_health = await self.check_database_health(db)
        system_health = self.check_system_resources()
        app_info = self.get_application_info()

        # Determine overall status
        overall_status = "healthy"
        if database_health.get("status") == "unhealthy":
            overall_status = "unhealthy"
        elif (system_health.get("cpu", {}).get("status") == "warning" or
              system_health.get("memory", {}).get("status") == "warning" or
              system_health.get("disk", {}).get("status") == "warning"):
            overall_status = "warning"

        return {
            "status": overall_status,
            "timestamp": time.time(),
            "application": app_info,
            "database": database_health,
            "system": system_health
        }


class MetricsCollector:
    """
    Collect and provide application metrics.
    """

    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.response_times = []
        self.start_time = time.time()

    def increment_request_count(self):
        """Increment total request count."""
        self.request_count += 1

    def increment_error_count(self):
        """Increment error count."""
        self.error_count += 1

    def add_response_time(self, response_time: float):
        """
        Add response time measurement.

        Args:
            response_time: Response time in seconds
        """
        self.response_times.append(response_time)
        # Keep only last 1000 measurements to prevent memory issues
        if len(self.response_times) > 1000:
            self.response_times = self.response_times[-1000:]

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current application metrics.

        Returns:
            Current metrics data
        """
        uptime = time.time() - self.start_time

        # Calculate response time statistics
        response_stats = {}
        if self.response_times:
            response_stats = {
                "count": len(self.response_times),
                "average_ms": round(sum(self.response_times) / len(self.response_times) * 1000, 2),
                "min_ms": round(min(self.response_times) * 1000, 2),
                "max_ms": round(max(self.response_times) * 1000, 2)
            }

        return {
            "uptime_seconds": round(uptime, 2),
            "requests": {
                "total": self.request_count,
                "errors": self.error_count,
                "success_rate": round((self.request_count - self.error_count) / max(self.request_count, 1) * 100, 2),
                "requests_per_second": round(self.request_count / max(uptime, 1), 2)
            },
            "response_times": response_stats,
            "timestamp": time.time()
        }


# Global instances
health_checker = HealthChecker()
metrics_collector = MetricsCollector()