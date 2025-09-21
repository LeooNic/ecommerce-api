#!/usr/bin/env python3
"""
Setup verification script for E-commerce API
Verifies that the environment meets all Phase 0 requirements
"""

import sys
import subprocess
import os
from pathlib import Path


def check_python_version():
    """Verify Python version is 3.10 or higher"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 10:
        print(f"[OK] Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print(f"[ERROR] Python {version.major}.{version.minor}.{version.micro} - Requires Python 3.10+")
        return False


def check_docker():
    """Verify Docker is installed and running"""
    try:
        result = subprocess.run(['docker', '--version'],
                              capture_output=True, text=True, check=True)
        print(f"[OK] Docker - {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[ERROR] Docker not found or not running")
        return False


def check_docker_compose():
    """Verify Docker Compose is available"""
    try:
        result = subprocess.run(['docker', 'compose', 'version'],
                              capture_output=True, text=True, check=True)
        print(f"[OK] Docker Compose - {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[ERROR] Docker Compose not found")
        return False


def check_required_files():
    """Verify all required Phase 0 files exist"""
    required_files = [
        'requirements.txt',
        'Dockerfile',
        'docker-compose.yml',
        'README.md',
        '.gitignore',
        '.env.example'
    ]

    all_files_exist = True
    for file_name in required_files:
        if Path(file_name).exists():
            print(f"[OK] {file_name} - Found")
        else:
            print(f"[ERROR] {file_name} - Missing")
            all_files_exist = False

    return all_files_exist


def check_virtual_environment():
    """Check if running in a virtual environment"""
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("[OK] Virtual environment - Active")
        return True
    else:
        print("[WARNING] Virtual environment - Not detected (recommended for local development)")
        return False


def main():
    """Run all verification checks"""
    print("E-commerce API - Phase 0 Setup Verification")
    print("=" * 50)

    checks = [
        ("Python Version", check_python_version),
        ("Required Files", check_required_files),
        ("Docker", check_docker),
        ("Docker Compose", check_docker_compose),
        ("Virtual Environment", check_virtual_environment),
    ]

    results = []
    for check_name, check_func in checks:
        print(f"\nChecking {check_name}:")
        results.append(check_func())

    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"All checks passed! ({passed}/{total})")
        print("\nPhase 0 setup is complete. Ready to proceed with Phase 1!")
    else:
        print(f"{passed}/{total} checks passed. Please address the issues above.")

    print("\nNext steps:")
    print("1. Create virtual environment: python -m venv venv")
    print("2. Activate virtual environment: venv\\Scripts\\activate (Windows) or source venv/bin/activate (Unix)")
    print("3. Install dependencies: pip install -r requirements.txt")
    print("4. Copy .env.example to .env and configure your settings")
    print("5. Start with Docker: docker-compose up")


if __name__ == "__main__":
    main()