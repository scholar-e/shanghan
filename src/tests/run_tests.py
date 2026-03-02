#!/usr/bin/env python3
"""Simple test runner for Shanghan-TCM v1 server."""

import subprocess
import sys
import os
import time
import requests
import json

PORT = 8765
BASE_URL = f"http://localhost:{PORT}"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def start_server():
    """Start the Flask server."""
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
            return server_process
        except requests.exceptions.ConnectionError:
            time.sleep(1)
    
    raise Exception("Server failed to start")

def stop_server(server):
    """Stop the Flask server."""
    server.terminate()
    try:
        server.wait(timeout=5)
    except:
        server.kill()

def test_home_page():
    """Test home page loads."""
    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert "Shanghan-TCM Evidence" in response.text
    print("✓ Home page loads")

def test_login_page():
    """Test login page loads."""
    response = requests.get(f"{BASE_URL}/login")
    assert response.status_code == 200
    assert "Sign In" in response.text
    print("✓ Login page loads")

def test_chat_redirect():
    """Test chat page redirects when not logged in."""
    response = requests.get(f"{BASE_URL}/chat", allow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers.get('Location', '')
    print("✓ Chat page redirects when not logged in")

def test_login_success():
    """Test successful login."""
    session = requests.Session()
    response = session.post(
        f"{BASE_URL}/api/login",
        json={"email": "prof@tcm.org", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert data['redirect'] == '/chat'
    
    chat_response = session.get(f"{BASE_URL}/chat")
    assert chat_response.status_code == 200
    print("✓ Login success")

def test_login_failure():
    """Test login failure with wrong password."""
    response = requests.post(
        f"{BASE_URL}/api/login",
        json={"email": "prof@tcm.org", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    data = response.json()
    assert data['success'] is False
    print("✓ Login failure")

def test_logout():
    """Test logout functionality."""
    session = requests.Session()
    session.post(
        f"{BASE_URL}/api/login",
        json={"email": "prof@tcm.org", "password": "password123"}
    )
    
    response = session.post(f"{BASE_URL}/api/logout")
    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    print("✓ Logout works")

def test_chat_requires_auth():
    """Test chat requires authentication."""
    response = requests.post(
        f"{BASE_URL}/api/chat",
        json={"message": "Hello"}
    )
    assert response.status_code == 401
    print("✓ Chat requires authentication")

def test_chat_message():
    """Test chat with valid message."""
    session = requests.Session()
    session.post(
        f"{BASE_URL}/api/login",
        json={"email": "prof@tcm.org", "password": "password123"}
    )
    
    response = session.post(
        f"{BASE_URL}/api/chat",
        json={"message": "What is Ma Huang?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert 'answer' in data
    assert 'sources' in data
    assert len(data['answer']) > 0
    print("✓ Chat message works")

def test_feedback():
    """Test feedback submission."""
    session = requests.Session()
    session.post(
        f"{BASE_URL}/api/login",
        json={"email": "prof@tcm.org", "password": "password123"}
    )
    
    response = session.post(
        f"{BASE_URL}/api/feedback",
        json={"message_id": "msg_1", "rating": "up", "feedback": "Great!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    
    feedback_dir = os.path.join(BASE_DIR, 'data', 'feedback')
    feedback_files = [f for f in os.listdir(feedback_dir) if f.startswith('feedback_')]
    assert len(feedback_files) > 0
    print("✓ Feedback submission works")

def test_data_directories():
    """Test data directories exist."""
    feedback_dir = os.path.join(BASE_DIR, 'data', 'feedback')
    conv_dir = os.path.join(BASE_DIR, 'data', 'conversations')
    assert os.path.exists(feedback_dir)
    assert os.path.exists(conv_dir)
    print("✓ Data directories exist")

def main():
    print("Starting tests for Shanghan-TCM v1...")
    
    server = None
    try:
        server = start_server()
        
        print("\n--- Running Tests ---\n")
        
        test_home_page()
        test_login_page()
        test_chat_redirect()
        test_login_success()
        test_login_failure()
        test_logout()
        test_chat_requires_auth()
        test_chat_message()
        test_feedback()
        test_data_directories()
        
        print("\n=== All tests passed! ===")
        
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if server:
            stop_server(server)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
