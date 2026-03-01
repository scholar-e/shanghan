"""Pytest configuration for Playwright tests."""

import pytest
import os
import subprocess
import sys
import time
import requests

PORT = 8765
BASE_URL = f"http://localhost:{PORT}"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line("markers", "asyncio: mark test as async")


@pytest.fixture(scope="session")
def server():
    """Start the Flask server for the session."""
    env = os.environ.copy()
    env['PORT'] = str(PORT)
    env['FLASK_DEBUG'] = 'false'
    
    server_process = subprocess.Popen(
        [sys.executable, 'server.py'],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=BASE_DIR
    )
    
    time.sleep(3)
    
    max_retries = 15
    for i in range(max_retries):
        try:
            requests.get(BASE_URL, timeout=2)
            break
        except requests.exceptions.ConnectionError:
            time.sleep(1)
    else:
        server_process.kill()
        raise Exception("Server failed to start")
    
    yield BASE_URL
    
    server_process.terminate()
    try:
        server_process.wait(timeout=5)
    except:
        server_process.kill()


@pytest.fixture(scope="session")
def base_url(server):
    """Provide base URL to tests."""
    return server
