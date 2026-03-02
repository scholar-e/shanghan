"""Playwright configuration for Shanghan-TCM v1 tests."""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = os.environ.get('PLAYWRIGHT_PORT', '8765')
BASE_URL = f"http://localhost:{PORT}"

def pytest_configure(config):
    """Configure Playwright."""
    config.addinivalue_line("markers", "slow: marks tests as slow")


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="Run tests in headed mode (visible browser)"
    )
