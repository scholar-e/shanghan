"""Test chat page with Playwright."""

import pytest


def login(page, base_url):
    """Helper to log in."""
    page.goto(f"{base_url}/login")
    page.fill("#email", "prof@tcm.org")
    page.fill("#password", "password123")
    page.click("#submitBtn")
    page.wait_for_url("**/chat", timeout=5000)


def test_chat_page_title(page, base_url):
    """Test that chat page has correct title."""
    login(page, base_url)
    title = page.title()
    assert "Chat" in title


def test_chat_page_header(page, base_url):
    """Test that chat page displays header."""
    login(page, base_url)
    logo = page.locator(".logo").text_content()
    assert "Shanghan-TCM Evidence" in logo


def test_chat_page_user_email_visible(page, base_url):
    """Test that user email is displayed."""
    login(page, base_url)
    user_email = page.locator(".user-email").text_content()
    assert "prof@tcm.org" in user_email


def test_chat_page_logout_button(page, base_url):
    """Test that logout button is visible."""
    login(page, base_url)
    logout_btn = page.locator(".logout-btn")
    assert logout_btn.is_visible()


def test_chat_page_welcome_message(page, base_url):
    """Test that welcome message is displayed."""
    login(page, base_url)
    welcome = page.locator(".welcome-message").text_content()
    assert "Welcome" in welcome


def test_chat_page_input_visible(page, base_url):
    """Test that chat input is visible."""
    login(page, base_url)
    message_input = page.locator("#messageInput")
    send_btn = page.locator("#sendBtn")
    message_input.wait_for()
    assert message_input.is_visible()
    assert send_btn.is_visible()


def test_chat_send_message(page, base_url):
    """Test sending a message."""
    login(page, base_url)
    
    message_input = page.locator("#messageInput")
    send_btn = page.locator("#sendBtn")
    
    message_input.fill("What is Ma Huang?")
    send_btn.click()
    
    page.wait_for_selector(".message.bot .message-content", timeout=30000)
    
    bot_messages = page.locator(".message.bot .message-content")
    count = bot_messages.count()
    assert count > 0
    
    last_message = bot_messages.nth(count - 1).text_content()
    assert len(last_message) > 0


def test_chat_sources_displayed(page, base_url):
    """Test that sources are displayed."""
    login(page, base_url)
    
    page.fill("#messageInput", "What is Ma Huang?")
    page.click("#sendBtn")
    
    page.wait_for_selector(".message.sources", timeout=30000)
    
    sources = page.locator(".source-item")
    count = sources.count()
    assert count > 0


def test_chat_enter_key_sends_message(page, base_url):
    """Test that Enter key sends message."""
    login(page, base_url)
    
    message_input = page.locator("#messageInput")
    message_input.fill("Test message")
    message_input.press("Enter")
    
    page.wait_for_selector(".message.bot .message-content", timeout=30000)


def test_chat_multiple_messages(page, base_url):
    """Test sending multiple messages."""
    login(page, base_url)
    
    page.fill("#messageInput", "Question 1")
    page.click("#sendBtn")
    page.wait_for_selector(".message.bot .message-content", timeout=30000)
    
    user_messages_before = page.locator(".message.user").count()
    
    page.fill("#messageInput", "Question 2")
    page.click("#sendBtn")
    page.wait_for_selector(".message.bot .message-content", timeout=30000)
    
    user_messages_after = page.locator(".message.user").count()
    assert user_messages_after > user_messages_before
