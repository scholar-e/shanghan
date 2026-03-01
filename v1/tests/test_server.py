#!/usr/bin/env python3
"""Test suite for Shanghan-TCM v1 server."""

import pytest
import json
import os
import sys
import time
import threading
import requests
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
SERVER_PATH = BASE_DIR / "server.py"
PORT = 8765
BASE_URL = f"http://localhost:{PORT}"

@pytest.fixture(scope="module")
def server():
    """Start the Flask server in a separate thread."""
    import subprocess
    
    env = os.environ.copy()
    env['PORT'] = str(PORT)
    env['FLASK_DEBUG'] = 'false'
    
    server_process = subprocess.Popen(
        [sys.executable, str(SERVER_PATH)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(BASE_DIR)
    )
    
    time.sleep(3)
    
    max_retries = 15
    for i in range(max_retries):
        try:
            requests.get(BASE_URL, timeout=2)
            break
        except requests.exceptions.ConnectionError:
            time.sleep(1)
    
    yield BASE_URL
    
    try:
        requests.post(f"{BASE_URL}/api/logout", timeout=2)
    except:
        pass
    
    server_process.terminate()
    try:
        server_process.wait(timeout=5)
    except:
        server_process.kill()


class TestHomePage:
    """Test home page routes."""
    
    def test_home_page_loads(self, server):
        """Test that home page loads successfully."""
        response = requests.get(f"{server}/")
        assert response.status_code == 200
        assert "Shanghan-TCM Evidence" in response.text
    
    def test_login_page_loads(self, server):
        """Test that login page loads successfully."""
        response = requests.get(f"{server}/login")
        assert response.status_code == 200
        assert "Sign In" in response.text
    
    def test_chat_page_redirects_when_not_logged_in(self, server):
        """Test that chat page redirects to login when not authenticated."""
        response = requests.get(f"{server}/chat", allow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers.get('Location', '')


class TestAuthentication:
    """Test authentication endpoints."""
    
    def test_login_success(self, server):
        """Test successful login with valid credentials."""
        session = requests.Session()
        response = session.post(
            f"{server}/api/login",
            json={"email": "prof@tcm.org", "password": "password123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['redirect'] == '/chat'
        
        chat_response = session.get(f"{server}/chat")
        assert chat_response.status_code == 200
    
    def test_login_failure_wrong_password(self, server):
        """Test login failure with wrong password."""
        response = requests.post(
            f"{server}/api/login",
            json={"email": "prof@tcm.org", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        data = response.json()
        assert data['success'] is False
        assert 'error' in data
    
    def test_login_failure_invalid_user(self, server):
        """Test login failure with invalid user."""
        response = requests.post(
            f"{server}/api/login",
            json={"email": "invalid@test.com", "password": "password123"}
        )
        assert response.status_code == 401
        data = response.json()
        assert data['success'] is False
    
    def test_logout(self, server):
        """Test logout functionality."""
        session = requests.Session()
        
        session.post(
            f"{server}/api/login",
            json={"email": "prof@tcm.org", "password": "password123"}
        )
        
        response = session.post(f"{server}/api/logout")
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        
        chat_response = session.get(f"{server}/chat", allow_redirects=False)
        assert chat_response.status_code == 302


class TestChatAPI:
    """Test chat API endpoints."""
    
    def test_chat_requires_authentication(self, server):
        """Test that chat endpoint requires authentication."""
        response = requests.post(
            f"{server}/api/chat",
            json={"message": "Hello"}
        )
        assert response.status_code == 401
    
    def test_chat_with_valid_message(self, server):
        """Test chat with a valid message."""
        session = requests.Session()
        session.post(
            f"{server}/api/login",
            json={"email": "prof@tcm.org", "password": "password123"}
        )
        
        response = session.post(
            f"{server}/api/chat",
            json={"message": "What is Ma Huang?"}
        )
        assert response.status_code == 200
        data = response.json()
        assert 'answer' in data
        assert 'sources' in data
        assert len(data['answer']) > 0
        assert len(data['sources']) > 0
    
    def test_chat_about_formula(self, server):
        """Test chat about a formula."""
        session = requests.Session()
        session.post(
            f"{server}/api/login",
            json={"email": "prof@tcm.org", "password": "password123"}
        )
        
        response = session.post(
            f"{server}/api/chat",
            json={"message": "Tell me about Gui Zhi Tang"}
        )
        assert response.status_code == 200
        data = response.json()
        assert 'answer' in data
        assert 'Gui Zhi' in data['answer'] or 'cinnamon' in data['answer'].lower()
    
    def test_chat_about_shang_han_lun(self, server):
        """Test chat about Shang Han Lun."""
        session = requests.Session()
        session.post(
            f"{server}/api/login",
            json={"email": "prof@tcm.org", "password": "password123"}
        )
        
        response = session.post(
            f"{server}/api/chat",
            json={"message": "What is the Shang Han Lun?"}
        )
        assert response.status_code == 200
        data = response.json()
        assert 'answer' in data
        assert 'Zhang Zhongjing' in data['answer'] or 'classical' in data['answer'].lower()


class TestFeedbackAPI:
    """Test feedback API endpoints."""
    
    def test_feedback_requires_authentication(self, server):
        """Test that feedback endpoint requires authentication."""
        response = requests.post(
            f"{server}/api/feedback",
            json={"message_id": "test_1", "rating": "up", "feedback": "Great!"}
        )
        assert response.status_code == 401
    
    def test_submit_feedback(self, server):
        """Test submitting feedback."""
        session = requests.Session()
        session.post(
            f"{server}/api/login",
            json={"email": "prof@tcm.org", "password": "password123"}
        )
        
        response = session.post(
            f"{server}/api/feedback",
            json={"message_id": "msg_1", "rating": "up", "feedback": "Very helpful!"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
    
    def test_feedback_saved_to_file(self, server):
        """Test that feedback is saved to a file."""
        session = requests.Session()
        session.post(
            f"{server}/api/login",
            json={"email": "prof@tcm.org", "password": "password123"}
        )
        
        session.post(
            f"{server}/api/feedback",
            json={"message_id": "msg_2", "rating": "down", "feedback": "Needs improvement"}
        )
        
        feedback_dir = BASE_DIR / "data" / "feedback"
        feedback_files = list(feedback_dir.glob("feedback_*.json"))
        assert len(feedback_files) > 0


class TestDataStorage:
    """Test data storage functionality."""
    
    def test_feedback_directory_exists(self):
        """Test that feedback directory exists."""
        feedback_dir = BASE_DIR / "data" / "feedback"
        assert feedback_dir.exists()
        assert feedback_dir.is_dir()
    
    def test_conversations_directory_exists(self):
        """Test that conversations directory exists."""
        conv_dir = BASE_DIR / "data" / "conversations"
        assert conv_dir.exists()
        assert conv_dir.is_dir()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
