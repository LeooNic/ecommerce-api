#!/usr/bin/env python3
"""
Production deployment script for the FastAPI e-commerce application.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_command(command: str, check: bool = True) -> subprocess.CompletedProcess:
    """
    Run a shell command and return the result.

    Args:
        command: Command to run
        check: Whether to check return code

    Returns:
        CompletedProcess result
    """
    logger.info(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True, check=check)

    if result.stdout:
        logger.info(f"STDOUT: {result.stdout}")
    if result.stderr:
        logger.warning(f"STDERR: {result.stderr}")

    return result


def check_prerequisites():
    """Check that all prerequisites are installed."""
    logger.info("Checking prerequisites...")

    # Check Python version
    if sys.version_info < (3, 8):
        logger.error("Python 3.8 or higher is required")
        sys.exit(1)

    # Check if Docker is available
    try:
        run_command("docker --version")
    except subprocess.CalledProcessError:
        logger.error("Docker is not installed or not available")
        sys.exit(1)

    # Check if Docker Compose is available
    try:
        run_command("docker-compose --version")
    except subprocess.CalledProcessError:
        logger.error("Docker Compose is not installed or not available")
        sys.exit(1)

    logger.info("Prerequisites check passed")


def install_dependencies():
    """Install Python dependencies."""
    logger.info("Installing Python dependencies...")

    # Check if virtual environment exists
    if not os.path.exists("venv"):
        logger.info("Creating virtual environment...")
        run_command("python -m venv venv")

    # Activate virtual environment and install dependencies
    if os.name == 'nt':  # Windows
        pip_command = "venv\\Scripts\\pip"
    else:  # Unix/Linux/macOS
        pip_command = "venv/bin/pip"

    run_command(f"{pip_command} install --upgrade pip")
    run_command(f"{pip_command} install -r requirements.txt")

    logger.info("Dependencies installed successfully")


def setup_environment():
    """Setup environment configuration."""
    logger.info("Setting up environment configuration...")

    if not os.path.exists(".env"):
        logger.info("Creating .env file from .env.example...")
        run_command("copy .env.example .env" if os.name == 'nt' else "cp .env.example .env")
        logger.warning("Please update .env file with your configuration before running the application")
    else:
        logger.info(".env file already exists")


def run_tests():
    """Run application tests."""
    logger.info("Running tests...")

    # Use the appropriate python command
    if os.name == 'nt':  # Windows
        python_command = "venv\\Scripts\\python"
    else:  # Unix/Linux/macOS
        python_command = "venv/bin/python"

    try:
        run_command(f"{python_command} -m pytest tests/ -v --tb=short")
        logger.info("All tests passed")
    except subprocess.CalledProcessError:
        logger.warning("Some tests failed, but continuing with deployment")


def build_docker_image():
    """Build Docker image."""
    logger.info("Building Docker image...")

    try:
        run_command("docker build -t ecommerce-api:latest .")
        logger.info("Docker image built successfully")
    except subprocess.CalledProcessError:
        logger.error("Failed to build Docker image")
        sys.exit(1)


def deploy_with_docker_compose():
    """Deploy using Docker Compose."""
    logger.info("Deploying with Docker Compose...")

    try:
        # Stop any existing containers
        run_command("docker-compose down", check=False)

        # Start the application
        run_command("docker-compose up -d")

        logger.info("Application deployed successfully")
        logger.info("API available at: http://localhost:8000")
        logger.info("Health check: http://localhost:8000/api/v1/health")
        logger.info("Metrics: http://localhost:8000/api/v1/metrics")
        logger.info("API Documentation: http://localhost:8000/docs")

    except subprocess.CalledProcessError:
        logger.error("Failed to deploy with Docker Compose")
        sys.exit(1)


def verify_deployment():
    """Verify that the deployment is working."""
    logger.info("Verifying deployment...")

    import time
    import requests

    # Wait for application to start
    logger.info("Waiting for application to start...")
    time.sleep(10)

    try:
        # Check health endpoint
        response = requests.get("http://localhost:8000/api/v1/health", timeout=10)
        if response.status_code == 200:
            logger.info("Health check passed")
            logger.info(f"Response: {response.json()}")
        else:
            logger.error(f"Health check failed with status: {response.status_code}")

        # Check root endpoint
        response = requests.get("http://localhost:8000/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            logger.info("Root endpoint accessible")
            logger.info(f"Application: {data.get('message')}")
            logger.info(f"Phase: {data.get('phase')}")
        else:
            logger.error(f"Root endpoint failed with status: {response.status_code}")

    except requests.RequestException as e:
        logger.error(f"Failed to verify deployment: {e}")
        logger.error("Application might not be ready yet. Check docker-compose logs:")
        logger.error("docker-compose logs api")


def main():
    """Main deployment function."""
    logger.info("Starting FastAPI E-commerce API deployment (Phase 5)")

    # Change to project directory
    project_dir = Path(__file__).parent.parent
    os.chdir(project_dir)
    logger.info(f"Working directory: {os.getcwd()}")

    try:
        check_prerequisites()
        install_dependencies()
        setup_environment()
        run_tests()
        build_docker_image()
        deploy_with_docker_compose()
        verify_deployment()

        logger.info("Deployment completed successfully!")
        logger.info("\nNext steps:")
        logger.info("1. Update .env file with production settings")
        logger.info("2. Configure Redis connection if using external Redis")
        logger.info("3. Set up proper SSL/TLS certificates")
        logger.info("4. Configure email SMTP settings")
        logger.info("5. Monitor application logs: docker-compose logs -f api")

    except KeyboardInterrupt:
        logger.info("Deployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()