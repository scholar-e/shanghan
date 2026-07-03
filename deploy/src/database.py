"""SQLite database module for Shanghan-TCM Evidence."""

import sqlite3
import threading
import json
import os
import functools
import logging
from datetime import datetime

from logger import get_logger

logger = get_logger("database")

_connection = None
_connection_lock = threading.Lock()
_write_lock = threading.Lock()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'shanghan.db')


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
        with _write_lock:
            return func(*args, **kwargs)
    return wrapper


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
        existing = json.loads(row["messages"])
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
    return json.loads(row["messages"]) if row else []


@with_db
def get_all_conversations():
    conn = get_connection()
    rows = conn.execute(
        "SELECT session_id, user_email, timestamp, messages FROM conversations ORDER BY timestamp DESC"
    ).fetchall()
    result = []
    for row in rows:
        msgs = json.loads(row["messages"])
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
        "SELECT * FROM conversations WHERE session_id = ?", (session_id,)
    ).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["messages"] = json.loads(data["messages"])
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
    terms = [t.strip() for t in query.replace('-', ' ').replace('_', ' ').split() if len(t.strip()) >= 2]
    if not terms:
        return []

    conditions = []
    params = []
    for term in terms:
        pattern = f"%{term}%"
        conditions.append("(content LIKE ? OR lesson_id LIKE ?)")
        params.extend([pattern, pattern])

    sql = f"""SELECT id, lesson_id, title, category, subcategory,
                     substr(content, 1, 300) AS preview, word_count
              FROM lessons WHERE {' OR '.join(conditions)}
              ORDER BY lesson_id LIMIT 10"""
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


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
    terms = [t.strip() for t in query.replace('-', ' ').split() if len(t.strip()) >= 2]
    if not terms:
        return []

    conditions = []
    params = []
    for term in terms:
        p = f"%{term}%"
        conditions.append("(original_zh LIKE ? OR translation_en LIKE ? OR channel LIKE ? OR pattern LIKE ? OR CAST(article_num AS TEXT) LIKE ?)")
        params.extend([p, p, p, p, p])

    sql = f"SELECT * FROM shl_articles WHERE {' OR '.join(conditions)} ORDER BY article_num LIMIT 10"
    rows = conn.execute(sql, params).fetchall()
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
