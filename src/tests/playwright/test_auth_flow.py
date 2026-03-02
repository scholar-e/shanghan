"""Test authentication flow with Playwright."""

import pytest


def test_full_login_chat_logout_flow(page, base_url):
    """Test complete user journey: home -> login -> chat -> logout -> home."""
    page.goto(base_url)
    
    sign_in = page.locator("a.btn", has_text="Sign In")
    sign_in.click()
    assert "/login" in page.url
    
    page.fill("#email", "prof@tcm.org")
    page.fill("#password", "password123")
    page.click("#submitBtn")
    page.wait_for_url("**/chat", timeout=5000)
    assert "/chat" in page.url
    
    user_email = page.locator(".user-email").text_content()
    assert "prof@tcm.org" in user_email
    
    logout_btn = page.locator(".logout-btn")
    logout_btn.click()
    page.wait_for_url("**/", timeout=5000)
    assert page.url == base_url + "/"


def test_chat_redirects_to_login_when_not_authenticated(page, base_url):
    """Test that unauthenticated user is redirected to login."""
    page.goto(f"{base_url}/chat")
    page.wait_for_url("**/login", timeout=5000)
    assert "/login" in page.url


def test_logout_clears_session(page, base_url):
    """Test that logout clears session and cannot access chat."""
    page.goto(f"{base_url}/login")
    page.fill("#email", "prof@tcm.org")
    page.fill("#password", "password123")
    page.click("#submitBtn")
    page.wait_for_url("**/chat", timeout=5000)
    
    page.click(".logout-btn")
    page.wait_for_url("**/", timeout=5000)
    
    page.goto(f"{base_url}/chat")
    page.wait_for_url("**/login", timeout=5000)


def test_login_page_redirects_to_chat_when_already_logged_in(page, base_url):
    """Test that logged in user is redirected to chat when visiting login page."""
    page.goto(f"{base_url}/login")
    page.fill("#email", "prof@tcm.org")
    page.fill("#password", "password123")
    page.click("#submitBtn")
    page.wait_for_url("**/chat", timeout=5000)
    
    page.goto(f"{base_url}/login")
    page.wait_for_url("**/chat", timeout=5000)
