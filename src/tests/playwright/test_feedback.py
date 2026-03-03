"""Test feedback system with Playwright."""

import pytest
import os


def login_and_send_message(page, base_url):
    """Helper to log in and send a message."""
    page.goto(f"{base_url}/login")
    page.fill("#email", "prof@tcm.org")
    page.fill("#password", "password123")
    page.click("#submitBtn")
    page.wait_for_url("**/chat", timeout=5000)
    
    page.fill("#messageInput", "What is Ma Huang?")
    page.click("#sendBtn")
    page.wait_for_selector(".message.bot .message-content", timeout=10000)


def test_feedback_buttons_visible(page, base_url):
    """Test that feedback buttons are visible after bot response."""
    login_and_send_message(page, base_url)
    
    feedback_container = page.locator(".feedback-container")
    feedback_container.wait_for()
    
    thumb_up = page.locator('.feedback-btn[title="Helpful"]')
    thumb_down = page.locator('.feedback-btn[title="Not helpful"]')
    
    assert thumb_up.is_visible()
    assert thumb_down.is_visible()


def test_feedback_popup_opens_on_thumb_up(page, base_url):
    """Test that feedback popup opens on thumb up click."""
    login_and_send_message(page, base_url)
    
    thumb_up = page.locator('.feedback-btn[title="Helpful"]')
    thumb_up.click()
    
    popup = page.locator(".feedback-popup")
    popup.wait_for()
    
    assert popup.is_visible()


def test_feedback_popup_opens_on_thumb_down(page, base_url):
    """Test that feedback popup opens on thumb down click."""
    login_and_send_message(page, base_url)
    
    thumb_down = page.locator('.feedback-btn[title="Not helpful"]')
    thumb_down.click()
    
    popup = page.locator(".feedback-popup")
    popup.wait_for()
    
    assert popup.is_visible()


def test_feedback_popup_has_textarea(page, base_url):
    """Test that feedback popup has textarea."""
    login_and_send_message(page, base_url)
    
    thumb_up = page.locator('.feedback-btn[title="Helpful"]')
    thumb_up.click()
    
    textarea = page.locator("#feedbackText")
    textarea.wait_for()
    assert textarea.is_visible()


def test_feedback_popup_has_buttons(page, base_url):
    """Test that feedback popup has submit and skip buttons."""
    login_and_send_message(page, base_url)
    
    thumb_up = page.locator('.feedback-btn[title="Helpful"]')
    thumb_up.click()
    
    submit_btn = page.locator(".feedback-submit")
    skip_btn = page.locator(".feedback-skip")
    
    submit_btn.wait_for()
    skip_btn.wait_for()
    
    assert submit_btn.is_visible()
    assert skip_btn.is_visible()


def test_feedback_popup_skip_closes(page, base_url):
    """Test that skip button closes popup."""
    login_and_send_message(page, base_url)
    
    thumb_up = page.locator('.feedback-btn[title="Helpful"]')
    thumb_up.click()
    
    popup = page.locator(".feedback-popup")
    popup.wait_for()
    
    skip_btn = page.locator(".feedback-skip")
    skip_btn.click()
    
    popup.wait_for(state="hidden", timeout=3000)


def test_feedback_popup_submit_closes(page, base_url):
    """Test that submit button closes popup."""
    login_and_send_message(page, base_url)
    
    thumb_up = page.locator('.feedback-btn[title="Helpful"]')
    thumb_up.click()
    
    popup = page.locator(".feedback-popup")
    popup.wait_for()
    
    page.fill("#feedbackText", "Great answer!")
    
    submit_btn = page.locator(".feedback-submit")
    submit_btn.click()
    
    popup.wait_for(state="hidden", timeout=3000)


def test_feedback_overlay_present(page, base_url):
    """Test that overlay is present when popup opens."""
    login_and_send_message(page, base_url)
    
    thumb_up = page.locator('.feedback-btn[title="Helpful"]')
    thumb_up.click()
    
    overlay = page.locator(".overlay")
    overlay.wait_for()
    assert overlay.is_visible()
