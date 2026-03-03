"""Test home page with Playwright."""

import pytest


def test_home_page_title(page, base_url):
    """Test that home page has correct title."""
    page.goto(base_url)
    title = page.title()
    assert "Shanghan-TCM Evidence" in title


def test_home_page_header(page, base_url):
    """Test that home page displays header."""
    page.goto(base_url)
    header = page.locator("h1").text_content()
    assert "Shanghan-TCM Evidence" in header


def test_home_page_content(page, base_url):
    """Test that home page displays content."""
    page.goto(base_url)
    content = page.locator(".content").text_content()
    assert "Overview" in content
    assert "What I Can Do" in content


def test_home_page_sign_in_button(page, base_url):
    """Test that sign in button is visible and clickable."""
    page.goto(base_url)
    sign_in_link = page.locator("a.btn", has_text="Sign In")
    sign_in_link.click()
    assert "/login" in page.url


def test_home_page_nonprofit_attribution(page, base_url):
    """Test that nonprofit attribution is visible."""
    page.goto(base_url)
    nonprofit = page.locator(".nonprofit").text_content()
    assert "WASFS" in nonprofit
