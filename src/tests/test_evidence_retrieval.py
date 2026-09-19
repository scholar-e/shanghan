"""Offline regression coverage for shared retrieval and tool-added evidence."""

import copy
import importlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import chat_engine as ce
import database as db
import retrieval
from evidence import EvidenceRegistry


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "corpus.db"))
    monkeypatch.setattr(db, "_connection", None)
    db.init_db()
    for number, song in [(9, 19), (26, 36), (73, 165), (100, 101), (101, 100)]:
        db.save_fuling_article(number, f"原文 {number}", song, f"宋文 {song}", "taiyang")
    db.save_zabing_article("z26_9", "26.9", "厚朴七物汤原文", "10.9", "金匮对照", "金匮", "第二十六章", "textbook_zabing.txt")
    db.save_zabing_article("z10_9", "10.9", "另一条原文", "8.1", "另一对照", "金匮", "第十章", "textbook_zabing.txt")
    db.save_lesson("lesson0002", "Lecture 2", "lectures", "", "private.txt", "Protected lecture passage: 五苓散")
    monkeypatch.setattr(ce, "get_active_ai_provider", lambda: ("deepseek", {"api_key": "offline-test"}))
    yield
    db.close_db()


@pytest.mark.parametrize("query,kind,reference,edition", [
    ("26.9", "decimal", "26.9", "fuling"),
    ("chapter 26 line 9", "decimal", "26.9", "fuling"),
    ("第26章第9条", "decimal", "26.9", "fuling"),
    ("金匮 10.9", "decimal", "10.9", "jingui"),
    ("Song edition line 100", "line", "100", "song"),
    ("100", "line", "100", "fuling"),
    ("formula #27", "formula", "27", "fuling"),
    ("第2讲", "lecture", "2", "fuling"),
    ("lecture 2", "lecture", "2", "fuling"),
    ("cough for 9 days", "text", "", "fuling"),
])
def test_reference_parser(query, kind, reference, edition):
    parsed = retrieval.parse_reference(query)
    assert (parsed.kind, parsed.reference, parsed.edition) == (kind, reference, edition)


@pytest.mark.parametrize("query,expected", [
    ("26.9", "26.9"), ("chapter 26 line 9", "26.9"),
    ("第26章第9条", "26.9"), ("金匮 10.9", "26.9"), ("10.9", "10.9"),
])
def test_public_chat_and_tool_resolve_same_decimal(corpus, query, expected):
    server = importlib.import_module("src.server")
    client = server.app.test_client()
    with client.session_transaction() as session:
        session["user"] = "prof@tcm.org"
    public = client.get("/api/search", query_string={"q": query}).get_json()
    tool = json.loads(ce.tool_search_articles(query))["fuling"]
    context, sources = ce.build_context(query)
    assert [r["fuling_article_num"] for r in public["textbook_entries"]] == [expected]
    assert public["textbook_entries"] == tool
    assert len(sources) == 1
    assert sources[0]["type"] == "zabing_article"
    assert expected in context
    assert not any(s["key"] in ("fuling_9", "fuling_26") for s in sources)


def test_exact_edition_filter_precedes_limit(corpus):
    # The same decimal can name a Fuling line or a comparison line.
    assert retrieval.search_textbook("10.9", limit=1)[0]["fuling_article_num"] == "10.9"
    assert retrieval.search_textbook("金匮 10.9", limit=1)[0]["fuling_article_num"] == "26.9"
    assert retrieval.search_textbook("宋本 10.9", limit=1) == []


@pytest.mark.parametrize("query,expected", [("100", 100), ("Songben line 100", 101)])
def test_integer_edition_resolution(corpus, query, expected):
    assert [r["fuling_article_num"] for r in retrieval.search_textbook(query)] == [expected]
    _, sources = ce.build_context(query)
    assert [s["key"] for s in sources] == [f"fuling_{expected}"]


def test_numbers_in_prose_are_not_line_references(corpus):
    assert retrieval.search_textbook("cough for 9 days") == []


def test_formula_number_and_pinyin_are_shared(corpus):
    server = importlib.import_module("src.server")
    client = server.app.test_client()
    with client.session_transaction() as session:
        session["user"] = "prof@tcm.org"
    for query in ("formula 27", "xiaochaihutang"):
        public = client.get("/api/search", query_string={"q": query, "mode": "name"}).get_json()
        keys = {r["key"] for group in public["formulas"].values() for r in group}
        tool = json.loads(ce.tool_search_formulas(query))
        _, sources = ce.build_context(query)
        assert keys
        assert {r["key"] for r in tool} <= keys
        assert {s["key"] for s in sources if s["type"] == "formula"} <= keys
    assert retrieval.search_textbook("formula 27") == []


def test_registry_deduplicates_by_identity_not_title():
    registry = EvidenceRegistry()
    source = {"title": "Same title", "type": "article", "key": "first"}
    assert registry.register(source, "Short passage") == 1
    assert registry.register(dict(source, title="Translated title"), "Full passage") == 1
    assert registry.register(dict(source, key="second"), "Other passage") == 2
    assert [s["citation_id"] for s in registry.sources] == [1, 2]
    assert "Full passage" in registry.context()
    assert "Full passage" in registry.sources[0]["content"]


def test_unregistered_citations_are_flagged():
    registry = EvidenceRegistry()
    registry.register({"title": "Known", "type": "article", "key": "1"}, "Evidence")
    answer, invalid = registry.validate_citations("Supported [1]. Mixed [1, 99]. Invalid [0]. Link [2](https://example.org).")
    assert invalid == [0, 99]
    assert "Supported [1]" in answer
    assert "[99]" not in answer and "[0]" not in answer
    assert "source unavailable" in answer
    assert "[2](https://example.org)" in answer


def mock_provider(monkeypatch, engine, provider, calls, final_answer):
    """Replay both wire protocols without any external HTTP requests."""
    payloads = []
    engine.client.provider = provider

    def send(payload):
        payloads.append(copy.deepcopy(payload))
        if len(payloads) == 1:
            if provider == "claude":
                return {"content": [{"type": "tool_use", "id": str(i), "name": name, "input": args}
                                    for i, (name, args) in enumerate(calls)]}
            return {"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [
                {"id": str(i), "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}
                for i, (name, args) in enumerate(calls)]}}]}
        if provider == "claude":
            return {"content": [{"type": "text", "text": final_answer}]}
        return {"choices": [{"message": {"role": "assistant", "content": final_answer}}]}

    monkeypatch.setattr(engine.client, "_send_claude_request" if provider == "claude" else "_send_request", send)
    return payloads


@pytest.mark.parametrize("provider", ["deepseek", "claude"])
def test_tool_evidence_reaches_answer_and_persistence(corpus, monkeypatch, provider):
    engine = ce.ChatEngine()
    payloads = mock_provider(monkeypatch, engine, provider, [
        ("get_fuling_article", {"article_num": 73}),
        ("search_lectures", {"query": "lecture 2"}),
    ], "Textbook [2]. Lecture [3]. Missing [99].")
    server = importlib.import_module("src.server")
    monkeypatch.setattr(server, "process_query", lambda query, history: engine.process_query(query, history))
    client = server.app.test_client()
    with client.session_transaction() as session:
        session["user"] = "prof@tcm.org"
        session["session_id"] = "tool-evidence-test"
    response = client.post("/api/chat", json={"message": "line 9"})
    assert response.status_code == 200
    data = response.get_json()
    assert [s["key"] for s in data["sources"]] == ["fuling_9", "fuling_73", "lesson0002"]
    assert [s["citation_id"] for s in data["sources"]] == [1, 2, 3]
    assert data["sources"][1]["source_id"] == "fuling_article:fuling_73"
    assert "[99]" not in data["answer"]
    assert "[2]" in data["answer"] and "[3]" in data["answer"]
    assert "content" not in data["sources"][2]
    assert "Protected lecture passage" not in json.dumps(data)
    stored = db.get_messages("tool-evidence-test")[-1]
    assert stored["sources"][2]["source_id"] == "lecture:lesson0002"
    assert "Protected lecture passage" in stored["context"]
    assert "原文 73" in stored["context"]
    wire = json.dumps(payloads[1], ensure_ascii=False)
    assert "citation" in wire and "[2]" in wire and "[3]" in wire
    assert "Protected lecture passage" in wire


@pytest.mark.parametrize("provider", ["deepseek", "claude"])
def test_retrieving_initial_source_does_not_renumber(corpus, monkeypatch, provider):
    engine = ce.ChatEngine()
    mock_provider(monkeypatch, engine, provider, [
        ("get_fuling_article", {"article_num": 9}),
        ("search_articles", {"query": "line 9"}),
    ], "Answer [1].")
    answer, sources, _, _ = engine.process_query("line 9")
    assert answer == "Answer [1]."
    assert len(sources) == 1 and sources[0]["citation_id"] == 1


def test_registry_is_request_local(corpus, monkeypatch):
    engine = ce.ChatEngine()
    monkeypatch.setattr(engine.client, "chat_with_tools", lambda *a, **kw: "Answer [1].")
    _, first, _, _ = engine.process_query("line 9")
    _, second, _, _ = engine.process_query("line 73")
    assert first[0]["key"] == "fuling_9" and second[0]["key"] == "fuling_73"
    assert first[0]["citation_id"] == second[0]["citation_id"] == 1


def test_long_context_preserves_citation_instructions(corpus, monkeypatch):
    db.get_connection().execute("UPDATE lessons SET content = ? WHERE lesson_id = ?", ("长篇讲义" * 6000, "lesson0002"))
    db.get_connection().commit()
    captured = []
    engine = ce.ChatEngine()
    monkeypatch.setattr(engine.client, "chat_with_tools", lambda messages, *a, **kw: captured.append(messages) or "Answer [1].")
    _, sources, context, _ = engine.process_query("lecture 2 " + "question " * 2000)
    prompt = captured[0][-1]["content"]
    assert "Available numbered sources:" in prompt
    assert "Tool results extend this list" in prompt
    assert "Focus on the most relevant information only." in prompt
    assert len(context) < 9000
    assert "content" not in sources[0]


def test_lecture_lookup_does_not_expose_public_text(corpus):
    server = importlib.import_module("src.server")
    client = server.app.test_client()
    with client.session_transaction() as session:
        session["user"] = "prof@tcm.org"
    result = client.get("/api/search?q=lecture+2").get_json()
    assert result["lessons"] == [] and result["textbook_entries"] == []
    registry = EvidenceRegistry()
    records = json.loads(ce.tool_search_lectures("第2讲", evidence=registry))
    assert "Protected lecture passage" in records[0]["text"]
    assert records[0]["citation"] == "[1]"
    assert "content" not in registry.sources[0]


def test_lecture_tool_can_retrieve_later_passages(corpus):
    content = "前文" * 6000 + "五苓散关键段落" + "后文" * 6000
    db.get_connection().execute("UPDATE lessons SET content = ? WHERE lesson_id = ?", (content, "lesson0002"))
    db.get_connection().commit()
    registry = EvidenceRegistry()
    data = json.loads(ce.tool_search_lectures("lecture 2 五苓散", evidence=registry))
    assert "五苓散关键段落" in data[0]["text"]
    assert len(data[0]["text"]) <= 8000
    assert "五苓散关键段落" in registry.context()


def test_zabing_keyword_tool_registers_sources(corpus):
    registry = EvidenceRegistry()
    data = json.loads(ce.tool_search_zabing_articles("厚朴七物汤", evidence=registry))
    assert data[0]["fuling_article_num"] == "26.9"
    assert data[0]["citation"] == "[1]"
    assert registry.sources[0]["source_id"] == "zabing_article:z26_9"


def test_invalid_tool_arguments_cannot_supply_evidence(corpus):
    engine = ce.ChatEngine()
    with pytest.raises(ValueError):
        engine.client._execute_tool("search_articles", {"query": "26.9", "evidence": {}}, EvidenceRegistry(), "shallow")
