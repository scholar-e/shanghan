"""Tests for mixed Chinese/English text query parsing."""

import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

import database as db
from chat_engine import build_context, tool_search_articles


def test_parse_text_query_extracts_chinese_phrase_and_article_number():
    terms = db.parse_text_query("第73条五苓散")

    assert "73" in terms
    assert "五苓散" in terms


def test_parse_text_query_handles_unspaced_chinese_sentence():
    terms = db.parse_text_query("太阳病，发汗后，大汗出")

    assert "太阳病" in terms
    assert "发汗后" in terms
    assert "大汗出" in terms


def test_song_article_number_search_returns_exact_match_first():
    results = db.search_articles("第73条五苓散")

    assert results
    assert results[0]["article_num"] == 73


def test_fuling_article_number_search_returns_exact_match_first():
    results = db.search_fuling_articles("涪陵古本第73条")

    assert results
    assert results[0]["fuling_article_num"] == 73


def test_lesson_search_uses_match_centered_preview():
    results = db.search_lessons("太阳病，发汗后，大汗出")

    assert results
    assert any(term in results[0]["preview"] for term in ("太阳", "发汗", "大汗"))


def test_ai_article_search_tool_returns_songben_and_yuanben():
    data = json.loads(tool_search_articles("第73条五苓散"))

    assert data["songben"]
    assert data["yuanben"]
    assert data["songben"][0]["article_num"] == 73
    assert data["yuanben"][0]["article_num"] == 73


def test_context_builder_includes_songben_and_yuanben_sources():
    _context, sources = build_context("第73条五苓散")
    titles = [source["title"] for source in sources]

    assert any("Article 73" in title for title in titles)
    assert any("Yuanben/Fuling Article 73" in title for title in titles)


def test_context_builder_reads_and_cites_specific_lecture_without_popup_content():
    context, sources = build_context("lecture 2")
    lecture = next(source for source in sources if source["type"] == "lecture")

    assert "[Lecture 2]" in context
    assert lecture["title"] == "Lecture 2"
    assert lecture["key"] == "lesson0002"
    assert lecture["hide_in_popup"] is True
    assert "content" not in lecture


def test_api_search_numeric_query_searches_original_text_even_in_name_mode():
    import server

    client = server.app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "prof@tcm.org"
        sess["session_id"] = "test-search-10"

    response = client.get("/api/search?q=10&mode=name")
    data = response.get_json()

    assert response.status_code == 200
    assert data["articles"]
    assert data["fuling_articles"]
    assert data["articles"][0]["article_num"] == 10
    assert data["fuling_articles"][0]["fuling_article_num"] == 10
