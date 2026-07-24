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


def test_fuling_numeric_search_does_not_include_same_songben_number():
    results = db.search_fuling_articles("fuling line 100")

    assert [row["fuling_article_num"] for row in results] == [100]


def test_bare_numeric_search_defaults_to_fuling_number_only():
    results = db.search_fuling_articles("100")

    assert [row["fuling_article_num"] for row in results] == [100]


def test_explicit_songben_numeric_search_uses_songben_number_only():
    results = db.search_fuling_articles("songben line 100")

    assert results
    assert all(row["song_article_num"] == 100 for row in results)
    assert not any(row["fuling_article_num"] == 100 for row in results)


def test_lesson_search_uses_match_centered_preview():
    results = db.search_lessons("太阳病，发汗后，大汗出")

    assert results
    assert any(term in results[0]["preview"] for term in ("太阳", "发汗", "大汗"))


def test_ai_article_search_tool_returns_unified_fuling_entries():
    data = json.loads(tool_search_articles("第73条五苓散"))

    assert data["fuling"]
    assert data["fuling"][0]["fuling_article_num"] == 73
    assert "songben_article_num" in data["fuling"][0]


def test_context_builder_uses_only_fuling_textbook_source():
    _context, sources = build_context("第73条五苓散")
    titles = [source["title"] for source in sources]

    assert "涪陵古本第 73 条（宋本第 165 条）" in titles
    assert not any("Yuanben" in title or "Shang Han Lun Article" in title for title in titles)


def test_context_builder_reads_and_cites_specific_lecture_without_popup_content():
    context, sources = build_context("lecture 2")
    lecture = next(source for source in sources if source["type"] == "lecture")

    assert "[Lecture 2]" in context
    assert lecture["title"] == "马寿椿医师第 2 讲"
    assert lecture["title_en"] == "Dr. Ma lecture 2"
    assert lecture["key"] == "lesson0002"
    assert lecture["hide_in_popup"] is True
    assert "content" not in lecture
    assert sum(1 for source in sources if source["type"] == "lecture") == 1


def test_api_chat_shows_lecture_citation_without_popup_content():
    import importlib

    server = importlib.import_module("src.server")

    client = server.app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "prof@tcm.org"
        sess["session_id"] = "test-public-lecture-citation"

    original = server.process_query
    server.process_query = lambda message, history: ("answer [1]", [
        {
            "title": "马寿椿医师第 6 讲",
            "title_zh": "马寿椿医师第 6 讲",
            "title_en": "Dr. Ma lecture 6",
            "type": "lecture",
            "key": "lesson0006",
            "hide_in_popup": True,
            "content": "protected lecture text",
        }
    ], "[Lecture 6] protected lecture text", [])
    try:
        response = client.post("/api/chat", json={"message": "test lecture citation"})
        data = response.get_json()
    finally:
        server.process_query = original

    assert response.status_code == 200
    assert data["sources"] == [{
        "title": "马寿椿医师第 6 讲",
        "title_zh": "马寿椿医师第 6 讲",
        "title_en": "Dr. Ma lecture 6",
        "type": "lecture",
        "key": "lesson0006",
        "hide_in_popup": True,
    }]


def test_api_search_numeric_query_searches_original_text_even_in_name_mode():
    import server

    client = server.app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "prof@tcm.org"
        sess["session_id"] = "test-search-10"

    response = client.get("/api/search?q=10&mode=name")
    data = response.get_json()

    assert response.status_code == 200
    assert not data["articles"]
    assert data["textbook_entries"]
    assert data["textbook_entries"][0]["fuling_article_num"] == 10
    assert "songben_article_num" in data["textbook_entries"][0]


def test_api_search_excludes_non_textbook_terminology_results():
    import server

    client = server.app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "prof@tcm.org"

    response = client.get("/api/search?q=liujing&mode=text")
    data = response.get_json()

    assert response.status_code == 200
    assert data["terminology"] == []
    assert data["lessons"] == []
    assert data["articles"] == []


def test_zabing_article_search_uses_chapter_line_reference():
    rows = db.search_zabing_articles("26.9")

    assert rows
    assert rows[0]["fuling_ref"] == "26.9"
    assert rows[0]["comparison_book"] == "金匮"
    assert rows[0]["comparison_ref"] == "10.9"
    assert "厚朴七物汤" in rows[0]["fuling_zh"]


def test_database_export_is_admin_only_and_returns_valid_sqlite():
    import server

    client = server.app.test_client()
    assert client.get("/admin/api/database/export").status_code == 401

    with client.session_transaction() as sess:
        sess["user"] = "regular@tcm.org"
    assert client.get("/admin/api/database/export").status_code == 403

    with client.session_transaction() as sess:
        sess["user"] = "prof@tcm.org"
    response = client.get("/admin/api/database/export")

    assert response.status_code == 200
    assert response.mimetype == "application/vnd.sqlite3"
    assert "attachment" in response.headers["Content-Disposition"]
    assert response.data.startswith(b"SQLite format 3\x00")
