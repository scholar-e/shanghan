"""SQLite database module for Shanghan-TCM Evidence."""

import sqlite3
import threading
import json
import os
import functools
import logging
import re
import time
from datetime import datetime

from logger import get_logger
from pinyin_utils import chinese_to_pinyin, normalize_pinyin

logger = get_logger("database")

_connection = None
_connection_lock = threading.Lock()
_write_lock = threading.Lock()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'shanghan.db')

TEXT_QUERY_STOPWORDS = {
    "第", "条", "条文", "文章", "原文", "经文", "宋本", "涪陵", "古本", "涪陵古本",
    "伤寒论", "伤寒", "查询", "搜索", "查找", "请问", "关于", "什么", "怎么", "如何",
    "解释", "说明", "比较", "版本", "the", "and", "for", "with", "what", "about",
    "article", "text", "search", "find", "show", "tell", "me", "does", "say", "please",
}


def _dedupe_preserve_order(values):
    seen = set()
    result = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def parse_text_query(query, max_terms=12):
    """Extract searchable terms from mixed Chinese/English text queries."""
    if not query:
        return []

    raw = str(query).strip()
    normalized = raw.lower()
    normalized = re.sub(r"[，。！？；：、（）《》【】“”‘’\[\](),.;:!?/_\-]+", " ", normalized)

    terms = []
    terms.extend(re.findall(r"(?:第\s*)?(\d{1,3})\s*(?:条文|条|章|article|art\b)", normalized, re.IGNORECASE))
    terms.extend(re.findall(r"\b\d{1,3}\b", normalized))

    for token in re.findall(r"[a-z][a-z0-9']*|[0-9]+", normalized):
        token = token.strip("'")
        if len(token) >= 2 and token not in TEXT_QUERY_STOPWORDS:
            terms.append(token)

    for chunk in re.findall(r"[\u4e00-\u9fff]+", raw):
        cleaned = chunk
        for stopword in sorted(TEXT_QUERY_STOPWORDS, key=len, reverse=True):
            if re.search(r"[\u4e00-\u9fff]", stopword):
                cleaned = cleaned.replace(stopword, " ")
        for part in cleaned.split():
            if len(part) < 2:
                continue
            if len(part) <= 12:
                terms.append(part)
            else:
                terms.append(part[:12])
            for size in (4, 3, 2):
                if len(part) > size:
                    for i in range(0, min(len(part) - size + 1, 8)):
                        terms.append(part[i:i + size])

    return _dedupe_preserve_order(terms)[:max_terms]


def _like_conditions(fields, terms):
    conditions = []
    params = []
    for term in terms:
        p = f"%{term}%"
        conditions.append("(" + " OR ".join(f"{field} LIKE ?" for field in fields) + ")")
        params.extend([p] * len(fields))
    return conditions, params


def _make_preview(content, terms, length=300):
    if not content:
        return ""
    match_pos = -1
    for term in terms:
        match_pos = content.lower().find(term.lower())
        if match_pos >= 0:
            break
    if match_pos < 0:
        return content[:length]
    start = max(0, match_pos - length // 3)
    end = min(len(content), start + length)
    return content[start:end]


def _is_latin_query(query):
    text = str(query or "")
    return bool(re.search(r"[A-Za-z]", text)) and not bool(re.search(r"[\u4e00-\u9fff]", text))


def _score_lesson_match(item, query, terms):
    """Rank lesson hits so broad/common terms do not always return early lessons."""
    content = item.get("content", "") or ""
    haystack = " ".join(
        str(item.get(field, "") or "")
        for field in ("lesson_id", "title", "category", "subcategory", "source_path")
    )
    haystack = f"{haystack} {content}".lower()
    query_text = str(query or "").strip().lower()
    score = 0

    explicit_lesson = re.search(r"(?:lecture|lesson|课(?:程)?|讲)\s*(\d{1,4})", query_text, re.IGNORECASE)
    if explicit_lesson:
        lesson_id = f"lesson{int(explicit_lesson.group(1)):04d}"
        if item.get("lesson_id") == lesson_id:
            score += 1000

    if query_text and len(query_text) >= 3 and query_text in haystack:
        score += 80

    for term in terms:
        if term.isdigit():
            continue
        term_lower = term.lower()
        count = haystack.count(term_lower)
        if count:
            score += min(count, 8) * max(len(term_lower), 2)
            if term_lower in str(item.get("title", "")).lower():
                score += 30
            if term_lower in str(item.get("category", "")).lower() or term_lower in str(item.get("subcategory", "")).lower():
                score += 20

    return score


def get_connection():
    global _connection
    if _connection is None:
        with _connection_lock:
            if _connection is None:
                _connection = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
                _connection.row_factory = sqlite3.Row
                _connection.execute("PRAGMA journal_mode=WAL")
                _connection.execute("PRAGMA foreign_keys=ON")
                _connection.execute("PRAGMA busy_timeout=30000")
    return _connection


def write_lock(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        last_error = None
        for attempt in range(6):
            try:
                with _write_lock:
                    return func(*args, **kwargs)
            except sqlite3.OperationalError as exc:
                if "locked" not in str(exc).lower():
                    raise
                last_error = exc
                time.sleep(0.25 * (attempt + 1))
        raise last_error
    return wrapper


@write_lock
def export_database(destination_path):
    """Write a transactionally consistent SQLite snapshot."""
    source = get_connection()
    snapshot = sqlite3.connect(destination_path)
    try:
        source.backup(snapshot)
    finally:
        snapshot.close()


@write_lock
def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            session_id TEXT PRIMARY KEY,
            user_email TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            messages TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT NOT NULL,
            rating TEXT NOT NULL,
            feedback_text TEXT DEFAULT '',
            timestamp TEXT NOT NULL,
            user_email TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS prescriptions (
            id TEXT PRIMARY KEY,
            user_email TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            query TEXT NOT NULL,
            response TEXT NOT NULL,
            formulas TEXT NOT NULL,
            message_id TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_email);
        CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback(user_email);
        CREATE INDEX IF NOT EXISTS idx_prescriptions_user ON prescriptions(user_email);

        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT NOT NULL,
            source_path TEXT NOT NULL,
            content TEXT NOT NULL,
            word_count INTEGER DEFAULT 0,
            indexed_at TEXT DEFAULT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_lessons_category ON lessons(category);
        CREATE INDEX IF NOT EXISTS idx_lessons_lesson_id ON lessons(lesson_id);

        CREATE TABLE IF NOT EXISTS shl_articles (
            article_num INTEGER PRIMARY KEY,
            channel TEXT NOT NULL,
            pattern TEXT DEFAULT '',
            original_zh TEXT NOT NULL,
            translation_en TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS fuling_articles (
            fuling_article_num INTEGER PRIMARY KEY,
            fuling_zh TEXT NOT NULL,
            song_article_num INTEGER DEFAULT NULL,
            song_zh TEXT DEFAULT NULL,
            channel TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS zabing_articles (
            entry_key TEXT PRIMARY KEY,
            fuling_ref TEXT NOT NULL,
            fuling_zh TEXT NOT NULL,
            comparison_ref TEXT DEFAULT NULL,
            comparison_zh TEXT DEFAULT NULL,
            comparison_book TEXT DEFAULT '金匮',
            chapter_title TEXT DEFAULT '',
            source_path TEXT DEFAULT ''
        );
    """)
    conn.commit()


def close_db():
    global _connection
    with _connection_lock:
        if _connection is not None:
            _connection.close()
            _connection = None


def with_db(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except sqlite3.Error as e:
            logger.error(f"Database error in {func.__name__}: {e}")
            raise
    return wrapper


# --- Conversations ---

@write_lock
@with_db
def save_conversation(session_id, user_email, timestamp, messages):
    conn = get_connection()
    conn.execute(
        """INSERT OR REPLACE INTO conversations (session_id, user_email, timestamp, messages)
           VALUES (?, ?, ?, ?)""",
        (session_id, user_email, timestamp, json.dumps(messages, ensure_ascii=False))
    )
    conn.commit()


@write_lock
@with_db
def append_messages(session_id, user_email, new_messages):
    conn = get_connection()
    row = conn.execute(
        "SELECT messages FROM conversations WHERE session_id = ?", (session_id,)
    ).fetchone()
    if row:
        try:
            existing = json.loads(row["messages"])
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Malformed conversation payload during append: {session_id}")
            existing = []
        existing.extend(new_messages)
        messages = existing
    else:
        messages = new_messages
    conn.execute(
        "INSERT OR REPLACE INTO conversations (session_id, user_email, timestamp, messages) VALUES (?, ?, ?, ?)",
        (session_id, user_email, datetime.now().isoformat(), json.dumps(messages, ensure_ascii=False))
    )
    conn.commit()


@with_db
def get_messages(session_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT messages FROM conversations WHERE session_id = ?", (session_id,)
    ).fetchone()
    if not row:
        return []
    try:
        return json.loads(row["messages"])
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"Malformed conversation payload during read: {session_id}")
        return []


@with_db
def get_all_conversations():
    conn = get_connection()
    rows = conn.execute(
        """SELECT session_id, user_email, timestamp, CAST(messages AS BLOB) AS messages
           FROM conversations ORDER BY timestamp DESC"""
    ).fetchall()
    result = []
    for row in rows:
        raw_messages = row["messages"]
        if isinstance(raw_messages, bytes):
            raw_messages = raw_messages.decode("utf-8", errors="replace")
        try:
            msgs = json.loads(raw_messages)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Malformed conversation payload: {row['session_id']}")
            msgs = []
        result.append({
            "session_id": row["session_id"],
            "user_email": row["user_email"],
            "timestamp": row["timestamp"],
            "message_count": len(msgs)
        })
    return result


@with_db
def get_conversation(session_id):
    conn = get_connection()
    row = conn.execute(
        """SELECT session_id, user_email, timestamp, CAST(messages AS BLOB) AS messages
           FROM conversations WHERE session_id = ?""", (session_id,)
    ).fetchone()
    if row is None:
        return None
    data = dict(row)
    raw_messages = data["messages"]
    if isinstance(raw_messages, bytes):
        raw_messages = raw_messages.decode("utf-8", errors="replace")
    try:
        data["messages"] = json.loads(raw_messages)
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"Malformed conversation payload: {session_id}")
        data["messages"] = []
    return data


# --- Feedback ---

@write_lock
@with_db
def save_feedback(message_id, rating, feedback_text, timestamp, user_email):
    conn = get_connection()
    conn.execute(
        """INSERT INTO feedback (message_id, rating, feedback_text, timestamp, user_email)
           VALUES (?, ?, ?, ?, ?)""",
        (message_id, rating, feedback_text, timestamp, user_email)
    )
    conn.commit()


@with_db
def get_all_feedback():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM feedback ORDER BY timestamp DESC"
    ).fetchall()
    return [dict(r) for r in rows]


# --- Prescriptions ---

@write_lock
@with_db
def save_prescription(prescription_id, user_email, timestamp, query, response, formulas, message_id):
    conn = get_connection()
    conn.execute(
        """INSERT OR REPLACE INTO prescriptions (id, user_email, timestamp, query, response, formulas, message_id)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (prescription_id, user_email, timestamp, query, response,
         json.dumps(formulas, ensure_ascii=False), message_id)
    )
    conn.commit()


@with_db
def get_prescriptions_for_user(user_email):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM prescriptions WHERE user_email = ? ORDER BY timestamp DESC",
        (user_email,)
    ).fetchall()
    result = []
    for row in rows:
        formulas_list = json.loads(row["formulas"])
        result.append({
            "id": row["id"],
            "timestamp": row["timestamp"],
            "query": row["query"][:100] + ("..." if len(row["query"]) > 100 else ""),
            "formula_count": len(formulas_list),
            "formula_names": [f.get("names", {}).get("zh", "") for f in formulas_list],
            "response_preview": row["response"][:150] + ("..." if len(row["response"]) > 150 else "")
        })
    return result


@with_db
def get_prescription(prescription_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM prescriptions WHERE id = ?", (prescription_id,)
    ).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["formulas"] = json.loads(data["formulas"])
    return data


# --- Lessons ---

@write_lock
@with_db
def save_lesson(lesson_id, title, category, subcategory, source_path, content):
    conn = get_connection()
    conn.execute(
        """INSERT OR REPLACE INTO lessons (lesson_id, title, category, subcategory, source_path, content, word_count)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (lesson_id, title, category, subcategory, source_path, content, len(content.split()))
    )
    conn.commit()


@with_db
def get_all_lessons():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, lesson_id, title, category, subcategory, source_path, word_count, indexed_at FROM lessons ORDER BY lesson_id"
    ).fetchall()
    return [dict(r) for r in rows]


@with_db
def get_lesson(lesson_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM lessons WHERE lesson_id = ?", (lesson_id,)).fetchone()
    return dict(row) if row else None


@with_db
def search_lessons(query):
    conn = get_connection()
    terms = parse_text_query(query)
    if not terms:
        return []

    keyword_terms = [term for term in terms if not term.isdigit()]
    lesson_number = re.search(r'(?:lecture|lesson|课(?:程)?|讲)\s*(\d{1,4})', str(query or ""), re.IGNORECASE)
    if not keyword_terms and not lesson_number:
        return []

    fields = ["content", "lesson_id", "title", "category", "subcategory", "source_path"]
    conditions, params = _like_conditions(fields, terms)

    sql = f"""SELECT id, lesson_id, title, category, subcategory,
                     content, word_count
              FROM lessons WHERE {' OR '.join(conditions)}
              ORDER BY lesson_id LIMIT 50"""
    rows = conn.execute(sql, params).fetchall()
    results = []
    seen_lesson_ids = set()
    for row in rows:
        item = dict(row)
        lesson_id = item.get("lesson_id")
        if lesson_id in seen_lesson_ids:
            continue
        seen_lesson_ids.add(lesson_id)
        score = _score_lesson_match(item, query, terms)
        if score <= 0:
            continue
        item["match_score"] = score
        item["preview"] = _make_preview(item.pop("content", ""), keyword_terms or terms)
        results.append(item)
    results.sort(key=lambda item: (-item["match_score"], item["lesson_id"]))
    return results[:50]


@with_db
def search_lessons_lesson_id(lesson_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM lessons WHERE lesson_id = ?", (lesson_id,)).fetchone()
    return dict(row) if row else None


@write_lock
@with_db
def clear_lessons():
    conn = get_connection()
    conn.execute("DELETE FROM lessons")
    conn.commit()


@with_db
def lesson_count():
    conn = get_connection()
    return conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]


# --- SHL Articles (原文) ---

@write_lock
@with_db
def save_article(article_num, channel, pattern, original_zh, translation_en):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO shl_articles (article_num, channel, pattern, original_zh, translation_en) VALUES (?, ?, ?, ?, ?)",
        (article_num, channel, pattern, original_zh, translation_en)
    )
    conn.commit()


@with_db
def get_article(article_num):
    conn = get_connection()
    row = conn.execute("SELECT * FROM shl_articles WHERE article_num = ?", (article_num,)).fetchone()
    return dict(row) if row else None


@with_db
def search_articles(query):
    conn = get_connection()
    terms = parse_text_query(query)
    if not terms:
        return []

    rows = []
    article_nums = [int(term) for term in terms if term.isdigit()]
    if article_nums:
        placeholders = ",".join("?" for _ in article_nums)
        rows.extend(conn.execute(
            f"SELECT * FROM shl_articles WHERE article_num IN ({placeholders}) ORDER BY article_num",
            article_nums
        ).fetchall())

    seen_nums = {row["article_num"] for row in rows}
    keyword_terms = [term for term in terms if not term.isdigit()]
    if not keyword_terms:
        return [dict(r) for r in rows[:10]]

    fields = ["original_zh", "translation_en", "channel", "pattern", "CAST(article_num AS TEXT)"]
    conditions, params = _like_conditions(fields, keyword_terms)

    sql = f"SELECT * FROM shl_articles WHERE {' OR '.join(conditions)} ORDER BY article_num LIMIT 50"
    rows.extend(row for row in conn.execute(sql, params).fetchall() if row["article_num"] not in seen_nums)
    return [dict(r) for r in rows]


@write_lock
@with_db
def clear_articles():
    conn = get_connection()
    conn.execute("DELETE FROM shl_articles")
    conn.commit()


@with_db
def article_count():
    conn = get_connection()
    return conn.execute("SELECT COUNT(*) FROM shl_articles").fetchone()[0]


# --- Fuling Articles (涪陵古本 原文) ---

@with_db
def get_fuling_by_song_article(song_article_num):
    """Get Fuling article(s) corresponding to a specific Song article number."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM fuling_articles WHERE song_article_num = ? ORDER BY fuling_article_num LIMIT 5",
        (song_article_num,)
    ).fetchall()
    return [dict(r) for r in rows]

@write_lock
@with_db
def save_fuling_article(fuling_article_num, fuling_zh, song_article_num, song_zh, channel):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO fuling_articles (fuling_article_num, fuling_zh, song_article_num, song_zh, channel) VALUES (?, ?, ?, ?, ?)",
        (fuling_article_num, fuling_zh, song_article_num, song_zh, channel)
    )
    conn.commit()


@with_db
def get_fuling_article(fuling_article_num):
    conn = get_connection()
    row = conn.execute("SELECT * FROM fuling_articles WHERE fuling_article_num = ?", (fuling_article_num,)).fetchone()
    return dict(row) if row else None


@write_lock
@with_db
def clear_zabing_articles():
    conn = get_connection()
    conn.execute("DELETE FROM zabing_articles")
    conn.commit()


@write_lock
@with_db
def save_zabing_article(entry_key, fuling_ref, fuling_zh, comparison_ref, comparison_zh, comparison_book, chapter_title, source_path):
    conn = get_connection()
    conn.execute(
        """INSERT OR REPLACE INTO zabing_articles
           (entry_key, fuling_ref, fuling_zh, comparison_ref, comparison_zh, comparison_book, chapter_title, source_path)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (entry_key, fuling_ref, fuling_zh, comparison_ref, comparison_zh, comparison_book, chapter_title, source_path),
    )
    conn.commit()


@with_db
def zabing_article_count():
    conn = get_connection()
    return conn.execute("SELECT COUNT(*) FROM zabing_articles").fetchone()[0]


@with_db
def search_zabing_articles(query):
    conn = get_connection()
    raw = str(query or "").strip()
    terms = parse_text_query(query)
    ref_terms = re.findall(r"\b\d{1,2}\.\d{1,3}\b", raw)
    if not terms and not ref_terms:
        return []

    rows = []
    seen = set()
    for ref in ref_terms:
        for row in conn.execute(
            """SELECT * FROM zabing_articles
               WHERE fuling_ref = ? OR comparison_ref = ?
               ORDER BY fuling_ref LIMIT 20""",
            (ref, ref),
        ).fetchall():
            if row["entry_key"] not in seen:
                rows.append(row)
                seen.add(row["entry_key"])

    keyword_terms = [term for term in terms if not term.isdigit()]
    if _is_latin_query(query):
        normalized_query = normalize_pinyin(query)
        for row in conn.execute("SELECT * FROM zabing_articles ORDER BY fuling_ref").fetchall():
            if row["entry_key"] in seen:
                continue
            pinyin_text = normalize_pinyin(chinese_to_pinyin(f"{row['fuling_zh']} {row['comparison_zh'] or ''}"))
            if normalized_query and normalized_query in pinyin_text:
                rows.append(row)
                seen.add(row["entry_key"])

    if keyword_terms:
        fields = ["fuling_zh", "comparison_zh", "chapter_title", "fuling_ref", "comparison_ref"]
        conditions, params = _like_conditions(fields, keyword_terms)
        sql = f"SELECT * FROM zabing_articles WHERE {' OR '.join(conditions)} ORDER BY fuling_ref LIMIT 100"
        for row in conn.execute(sql, params).fetchall():
            if row["entry_key"] not in seen:
                rows.append(row)
                seen.add(row["entry_key"])

    return [dict(row) for row in rows[:100]]


@with_db
def search_fuling_articles(query):
    conn = get_connection()
    terms = parse_text_query(query)
    if not terms:
        return []

    rows = []
    article_nums = [int(term) for term in terms if term.isdigit()]
    if article_nums:
        placeholders = ",".join("?" for _ in article_nums)
        query_lower = query.lower()
        prefer_song = "宋本" in query or "song" in query_lower
        number_column = "song_article_num" if prefer_song else "fuling_article_num"
        rows.extend(conn.execute(
            f"""
            SELECT * FROM fuling_articles
            WHERE {number_column} IN ({placeholders})
            ORDER BY fuling_article_num
            """,
            article_nums
        ).fetchall())

    seen_nums = {row["fuling_article_num"] for row in rows}
    keyword_terms = [term for term in terms if not term.isdigit()]
    if _is_latin_query(query):
        normalized_query = normalize_pinyin(query)
        for row in conn.execute("SELECT * FROM fuling_articles ORDER BY fuling_article_num").fetchall():
            if row["fuling_article_num"] in seen_nums:
                continue
            pinyin_text = normalize_pinyin(chinese_to_pinyin(f"{row['fuling_zh']} {row['song_zh']}"))
            if normalized_query and normalized_query in pinyin_text:
                rows.append(row)
                seen_nums.add(row["fuling_article_num"])

    if not keyword_terms:
        return [dict(r) for r in rows[:50]]

    fields = ["fuling_zh", "song_zh", "channel", "CAST(fuling_article_num AS TEXT)", "CAST(song_article_num AS TEXT)"]
    conditions, params = _like_conditions(fields, keyword_terms)

    sql = f"SELECT * FROM fuling_articles WHERE {' OR '.join(conditions)} ORDER BY fuling_article_num LIMIT 50"
    rows.extend(row for row in conn.execute(sql, params).fetchall() if row["fuling_article_num"] not in seen_nums)
    return [dict(r) for r in rows]


@write_lock
@with_db
def clear_fuling_articles():
    conn = get_connection()
    conn.execute("DELETE FROM fuling_articles")
    conn.commit()


@with_db
def fuling_article_count():
    conn = get_connection()
    return conn.execute("SELECT COUNT(*) FROM fuling_articles").fetchone()[0]
