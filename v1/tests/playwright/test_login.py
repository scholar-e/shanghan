"""Test login page with Playwright."""

import pytest


def test_login_page_title(page, base_url):
    """Test that login page has correct title."""
    page.goto(f"{base_url}/login")
    title = page.title()
    assert "Sign In" in title


def test_login_page_form_elements(page, base_url):
    """Test that login form has required elements."""
    page.goto(f"{base_url}/login")
    
    email_input = page.locator("#email")
    password_input = page.locator("#password")
    submit_btn = page.locator("#submitBtn")
    
    email_input.wait_for()
    password_input.wait_for()
    submit_btn.wait_for()
    
    assert email_input.is_visible()
    assert password_input.is_visible()
    assert submit_btn.is_visible()


def test_login_success(page, base_url):
    """Test successful login flow."""
    page.goto(f"{base_url}/login")
    
    page.fill("#email", "prof@tcm.org")
    page.fill("#password", "password123")
    page.click("#submitBtn")
    
    page.wait_for_url("**/chat", timeout=5000)
    assert "/chat" in page.url


def test_login_failure_wrong_password(page, base_url):
    """Test login failure with wrong password."""
    page.goto(f"{base_url}/login")
    
    page.fill("#email", "prof@tcm.org")
    page.fill("#password", "wrongpassword")
    page.click("#submitBtn")
    
    error = page.locator("#error")
    error.wait_for()
    assert error.is_visible()
    assert "Invalid" in error.text_content()


def test_login_failure_invalid_user(page, base_url):
    """Test login failure with invalid user."""
    page.goto(f"{base_url}/login")
    
    page.fill("#email", "invalid@test.com")
    page.fill("#password", "password123")
    page.click("#submitBtn")
    
    error = page.locator("#error")
    error.wait_for()
    assert error.is_visible()


def test_login_back_to_home(page, base_url):
    """Test back to home link."""
    page.goto(f"{base_url}/login")
    
    back_link = page.locator(".back-link a")
    back_link.click()
    
    assert page.url == base_url + "/"
