#!/usr/bin/env python3
"""Shanghan-TCM Evidence v1 Server"""

import os
import sys
import json
import uuid
import hashlib
import time
import functools
import glob
import logging
import tempfile
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, make_response, send_file, after_this_request
from logger import setup_logging, get_logger, log_request, log_error, log_user_action
from knowledge_base import FORMULAS, TERMINOLOGY
from formula_intake import needs_formula_followup, formula_followup_response
import database as db

log = setup_logging("shanghan", level=logging.DEBUG)
logger = get_logger("server")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load .env file from project root or src/ directory
def load_env_file():
    for path in [os.path.join(BASE_DIR, '..', '.env'), os.path.join(BASE_DIR, '.env')]:
        env_path = os.path.abspath(path)
        if os.path.isfile(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, _, val = line.partition('=')
                        key, val = key.strip(), val.strip().strip("'\"")
                        if key not in os.environ:
                            os.environ[key] = val
            break

load_env_file()
db.init_db()

logger.info("=" * 60)
logger.info("Shanghan-TCM Evidence v1 Server Starting")
logger.info(f"Base Dir: {BASE_DIR}")
logger.info(f"Database: {db.DB_PATH}")
logger.info("=" * 60)

app = Flask(__name__)
secret_key = os.environ.get('SECRET_KEY')
if not secret_key:
    if os.environ.get('FLASK_DEBUG', 'true').lower() == 'true':
        secret_key = 'shanghan-tcm-secret-key-v1-dev'
        logger.warning("Using default secret key for development. Set SECRET_KEY env var for production.")
    else:
        logger.error("SECRET_KEY environment variable is required for production")
        raise ValueError("SECRET_KEY environment variable is required for production")
app.secret_key = secret_key
logger.info("Flask app created")

# Security headers middleware
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses."""
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # Enable XSS protection
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # HSTS - only in production
    if os.environ.get('FLASK_DEBUG', 'true').lower() != 'true':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    logger.debug(f"Security headers added to {request.path}")
    return response

PROFESSIONAL_USERS = {
    'prof@tcm.org': 'password123',  # Admin user
    'regular@tcm.org': 'userpass123'  # Regular user
}

def admin_required(func):
    """Decorator to require admin access."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            logger.warning("Admin access denied: not authenticated")
            return jsonify({'error': 'Authentication required'}), 401
        user = session.get('user')
        if user != 'prof@tcm.org':
            logger.warning(f"Admin access denied for user: {user}")
            return jsonify({'error': 'Admin access required'}), 403
        return func(*args, **kwargs)
    return wrapper

def log_route(func):
    """Decorator to log route calls."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        method = request.method
        path = request.path
        user = session.get('user', 'anonymous')
        
        logger.debug(f"Route call: {method} {path} | User: {user}")
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            status = getattr(result, 'status_code', 200)
            log_request(logger, method, path, status, duration)
            return result
        except Exception as e:
            duration = time.time() - start_time
            log_error(logger, e, f"{method} {path}")
            raise
    
    return wrapper

def get_language():
    """Simple language detection from session or cookie. Default Chinese."""
    if 'language' in session:
        return session['language']
    lang_cookie = request.cookies.get('language')
    if lang_cookie in ('en', 'zh'):
        return lang_cookie
    return 'zh'  # Default Chinese

@app.route('/')
@log_route
def home():
    logger.info("Home page accessed")
    return render_template('home.html')

@app.route('/en')
@log_route
def home_en():
    logger.info("English home page accessed")
    session['language'] = 'en'
    response = make_response(render_template('home_en.html'))
    response.set_cookie('language', 'en', max_age=365*24*60*60)
    return response

@app.route('/login')
@log_route
def login():
    logger.info(f"Login page accessed | User in session: {'user' in session}")
    if 'user' in session:
        logger.info(f"User {session.get('user')} already logged in, redirecting to chat")
        return redirect(url_for('chat'))
    return render_template('login.html')

@app.route('/chat')
@log_route
def chat():
    logger.info(f"Chat page accessed | Authenticated: {'user' in session}")
    if 'user' not in session:
        logger.warning("Unauthorized chat access attempt, redirecting to login")
        return redirect(url_for('login'))
    logger.info(f"Serving chat to user: {session['user']}")
    return render_template(
        'chat.html',
        user=session['user'],
        admin_enabled=True,
        feedback_enabled=True,
        formulas_json=json.dumps(FORMULAS, ensure_ascii=False),
    )

@app.route('/en/login')
@log_route
def login_en():
    logger.info(f"English login page accessed | User in session: {'user' in session}")
    if 'user' in session:
        logger.info(f"User {session.get('user')} already logged in, redirecting to chat")
        return redirect(url_for('chat_en'))
    response = make_response(render_template('login_en.html'))
    response.set_cookie('language', 'en', max_age=365*24*60*60)
    session['language'] = 'en'
    return response

@app.route('/en/chat')
@log_route
def chat_en():
    logger.info(f"English chat page accessed | Authenticated: {'user' in session}")
    if 'user' not in session:
        logger.warning("Unauthorized English chat access attempt, redirecting to login")
        return redirect(url_for('login_en'))
    logger.info(f"Serving English chat to user: {session['user']}")
    response = make_response(render_template(
        'chat_en.html',
        user=session['user'],
        admin_enabled=True,
        feedback_enabled=True,
        formulas_json=json.dumps(FORMULAS, ensure_ascii=False),
    ))
    response.set_cookie('language', 'en', max_age=365*24*60*60)
    session['language'] = 'en'
    return response

@app.route('/api/login', methods=['POST'])
@log_route
def api_login():
    data = request.json
    email = data.get('email', '')
    password = data.get('password', '')
    logger.info(f"Login attempt for email: {email}")
    
    if email in PROFESSIONAL_USERS and PROFESSIONAL_USERS[email] == password:
        session['user'] = email
        session['session_id'] = hashlib.md5(f"{email}{datetime.now().isoformat()}".encode()).hexdigest()
        logger.info(f"Login successful for: {email}")
        log_user_action(logger, email, "LOGIN", "Success")
        return jsonify({'success': True, 'redirect': url_for('chat')})
    
    logger.warning(f"Login failed for: {email} - Invalid credentials")
    log_user_action(logger, email, "LOGIN", "Failed - Invalid credentials")
    return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
@log_route
def api_logout():
    user = session.get('user')
    logger.info(f"Logout request for user: {user}")
    session.clear()
    log_user_action(logger, user, "LOGOUT", "Success")
    logger.info(f"Logout completed for user: {user}")
    return jsonify({'success': True})

@app.route('/api/chat', methods=['POST'])
@log_route
def api_chat():
    user = session.get('user')
    logger.info(f"Chat request from user: {user}")
    
    if 'user' not in session:
        logger.warning(f"Unauthorized chat attempt from IP: {request.remote_addr}")
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    message = data.get('message', '')
    logger.info(f"User message: {message[:100]}...")
    
    conversation_history = db.get_messages(session['session_id'])
    
    user_msg = {
        'role': 'user',
        'content': message,
        'timestamp': datetime.now().isoformat()
    }
    db.append_messages(session['session_id'], session['user'], [user_msg])
    
    logger.debug(f"Processing query: {message[:50]}... | History: {len(conversation_history)} messages")
    answer, sources, context, ai_formulas = process_query(message, conversation_history)
    logger.debug(f"Query processed, answer length: {len(answer)} chars, sources: {len(sources)}, ai_formulas: {len(ai_formulas)}, context length: {len(context)} chars")
    
    # Auto-save prescription if response contains formula data
    prescription_info = None
    
    # Collect formulas from knowledge base sources
    formulas_data = []
    for s in sources:
        if isinstance(s, dict) and s.get("type") == "formula":
            key = s.get("key", "")
            if key and key in FORMULAS:
                formulas_data.append(FORMULAS[key])
    
    # Include AI-generated formulas (not already in formulas_data)
    known_zh = {f.get("names", {}).get("zh", "") for f in formulas_data}
    for f in ai_formulas:
        f_zh = f.get("names", {}).get("zh", "") or f.get("name_zh", "")
        if f_zh and f_zh not in known_zh:
            normalized = {
                "names": {"zh": f_zh, "pinyin": f.get("names", {}).get("pinyin", f.get("name_pinyin", "")), "en": f.get("names", {}).get("en", "")},
                "composition": f.get("composition", []),
                "indications": f.get("indications", ""),
                "functions": f.get("functions", ""),
                "pattern": f.get("pattern", ""),
                "_ai_generated": True
            }
            formulas_data.append(normalized)
            known_zh.add(f_zh)
    
    if formulas_data:
        prescription_id = uuid.uuid4().hex[:12]
        db.save_prescription(
            prescription_id, user, datetime.now().isoformat(),
            message, answer, formulas_data, f"msg_{len(conversation_history) + 2}"
        )
        logger.info(f"Prescription auto-saved: {prescription_id} ({len(formulas_data)} formulas)")
        ai_count = sum(1 for f in formulas_data if f.get("_ai_generated"))
        if ai_count:
            logger.info(f"  Includes {ai_count} AI-generated formula(s)")
        prescription_info = {
            "id": prescription_id,
            "formula_count": len(formulas_data),
            "formula_names": [f.get("names", {}).get("zh", "") for f in formulas_data]
        }
    
    session_sources = [
        {"title": s["title"]} if isinstance(s, dict) else s
        for s in sources
    ]
    assistant_msg = {
        'role': 'assistant',
        'content': answer,
        'sources': session_sources,
        'context': context,
        'timestamp': datetime.now().isoformat()
    }
    db.append_messages(session['session_id'], session['user'], [assistant_msg])
    
    total_msgs = len(conversation_history) + 2
    message_id = f"msg_{total_msgs}"
    
    logger.info(f"Chat response sent to user: {user} | Msg ID: {message_id}")
    response_data = {
        'answer': answer,
        'sources': sources,
        'message_id': message_id
    }
    if prescription_info:
        response_data['prescription'] = prescription_info
    return jsonify(response_data)

@app.route('/api/feedback', methods=['POST'])
@log_route
def api_feedback():
    user = session.get('user')
    logger.info(f"Feedback request from user: {user}")
    
    if 'user' not in session:
        logger.warning("Unauthorized feedback attempt")
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    message_id = data.get('message_id')
    rating = data.get('rating')
    feedback_text = data.get('feedback', '')
    
    logger.info(f"Feedback received: Message={message_id}, Rating={rating}")
    logger.debug(f"Feedback text: {feedback_text[:100] if feedback_text else '(empty)'}")

    db.save_feedback(message_id, rating, feedback_text, datetime.now().isoformat(), session['user'])
    logger.info("Feedback saved to database")
    log_user_action(logger, session['user'], "FEEDBACK", f"Rating={rating}, Message={message_id}")
    
    return jsonify({'success': True})

@app.route('/admin')
@log_route
def admin():
    if 'user' not in session:
        logger.warning("Admin page access denied: not logged in")
        return redirect(url_for('login'))
    user = session.get('user')
    if user != 'prof@tcm.org':
        logger.warning(f"Admin page access denied for user: {user}")
        return redirect(url_for('home'))
    return render_template('admin.html')

@app.route('/admin/api/logs')
@log_route
@admin_required
def admin_logs():
    log_files = glob.glob(os.path.join(BASE_DIR, 'logs', '*.log'))
    log_files.sort(reverse=True)
    logs = []
    for log_file in log_files[:1]:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()[-1000:]
            for line in lines:
                parts = line.strip().split(' | ')
                if len(parts) >= 5:
                    logs.append({
                        'timestamp': parts[0],
                        'level': parts[1],
                        'location': parts[2],
                        'function': parts[3],
                        'message': parts[4]
                    })
                else:
                    logs.append({'raw': line.strip()})
    return jsonify({'logs': logs})

@app.route('/admin/api/conversations')
@log_route
@admin_required
def admin_conversations():
    conversations = db.get_all_conversations()
    return jsonify({'conversations': conversations})

@app.route('/admin/api/conversation/<session_id>')
@log_route
@admin_required
def admin_conversation(session_id):
    data = db.get_conversation(session_id)
    if data is None:
        return jsonify({'error': 'Conversation not found'}), 404
    return jsonify(data)

@app.route('/admin/api/feedback')
@log_route
@admin_required
def admin_feedback():
    feedbacks = db.get_all_feedback()
    return jsonify({'feedbacks': feedbacks})


@app.route('/admin/api/database/export')
@log_route
@admin_required
def admin_export_database():
    """Download a consistent snapshot of the complete SQLite database."""
    fd, snapshot_path = tempfile.mkstemp(prefix='shanghan-export-', suffix='.db')
    os.close(fd)
    try:
        db.export_database(snapshot_path)
    except Exception:
        if os.path.exists(snapshot_path):
            os.unlink(snapshot_path)
        raise

    @after_this_request
    def remove_snapshot(response):
        try:
            os.unlink(snapshot_path)
        except OSError:
            logger.warning(f"Could not remove database export snapshot: {snapshot_path}")
        return response

    filename = f"shanghan-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
    logger.info(f"Database exported by admin: {session.get('user')}")
    return send_file(
        snapshot_path,
        mimetype='application/vnd.sqlite3',
        as_attachment=True,
        download_name=filename,
        conditional=False,
    )

@app.route('/api/search', methods=['GET'])
@log_route
def api_search():
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    query = request.args.get('q', '').strip().lower()
    mode = request.args.get('mode', 'text')  # 'name' or 'text'

    if not query:
        return jsonify({'query': query, 'formulas': {}, 'lessons': [], 'articles': [], 'terminology': [], 'total': 0})

    parsed_terms = db.parse_text_query(query)
    if any(term.isdigit() for term in parsed_terms):
        mode = 'text'

    # ── Formulas ──
    formula_results = []
    for key, formula in FORMULAS.items():
        names = formula['names']
        matches = []
        for lang, name in names.items():
            if query in name.lower():
                label = {'zh': '中文名', 'pinyin': '拼音', 'en': '英文名'}.get(lang, lang)
                matches.append(f"名称 ({label})")
        if mode == 'text':
            for i, herb in enumerate(formula['composition']):
                for field in ['herb', 'pinyin', 'en']:
                    if query in herb[field].lower():
                        label = {'herb': '中文', 'pinyin': '拼音', 'en': '英文'}.get(field, field)
                        matches.append(f"组成 {i+1} ({label}: {herb[field]})")
            if query in formula['indications'].lower():
                matches.append("主治")
            if query in formula['functions'].lower():
                matches.append("功能")
            if query in formula['pattern'].lower():
                matches.append("证型")
        if matches:
            pattern = formula['pattern']
            if ' with ' in pattern:
                category = pattern.split(' with ')[0].strip()
            elif ' - ' in pattern:
                category = pattern.split(' - ')[0].strip()
            elif '–' in pattern:
                category = pattern.split('–')[0].strip()
            else:
                category = pattern.strip()
            formula_results.append({
                'key': key,
                'names': names,
                'composition': formula['composition'],
                'indications': formula['indications'],
                'functions': formula['functions'],
                'pattern': pattern,
                'category': category,
                'matches': matches,
            })

    formula_categories = {}
    for r in formula_results:
        cat = r.pop('category')
        formula_categories.setdefault(cat, []).append(r)

    # ── Terminology ──
    term_results = []
    for term, info in TERMINOLOGY.items():
        if query in term.lower() or query in info.get('en', '').lower() or query in info.get('pinyin', '').lower():
            term_results.append({
                'term': term,
                'pinyin': info.get('pinyin', ''),
                'en': info.get('en', '')
            })

    # ── Articles (原文) — only in text mode ──
    textbook_results = []
    if mode == 'text':
        # Fuling is the canonical textbook entry. Songben is metadata on that
        # entry, never a separate search result.
        try:
            for r in db.search_fuling_articles(query):
                textbook_results.append({
                    'fuling_article_num': r['fuling_article_num'],
                    'fuling_zh': r['fuling_zh'],
                    'songben_article_num': r['song_article_num'],
                    'songben_zh': r['song_zh'],
                    'channel': r['channel']
                })
        except Exception:
            pass

    total = len(textbook_results) + len(formula_results) + len(term_results)
    logger.info(f"Search: q='{query}' => {len(textbook_results)} Fuling textbook entries, {len(formula_results)} formulas, {len(term_results)} terms")
    return jsonify({
        'query': query,
        'formulas': formula_categories,
        'categories': formula_categories,
        'terminology': term_results,
        'textbook_entries': textbook_results,
        'articles': [],
        'fuling_articles': textbook_results,
        'total': total,
    })


@app.route('/health')
@log_route
def health():
    """Health check endpoint for load balancers and monitoring."""
    return jsonify({
        'status': 'healthy',
        'service': 'shanghan-tcm-evidence',
        'version': 'v1',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/debug/context')
@log_route
def debug_context():
    """Debug endpoint: show what build_context returns for a query."""
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'error': 'Provide ?q=query'}), 400
    from chat_engine import build_context
    ctx, sources = build_context(q)
    # Check for Fuling articles in DB
    fuling_matches = []
    try:
        fuling_matches = [{'article_num': r['fuling_article_num'], 'fuling_zh': r['fuling_zh'][:100]} for r in db.search_fuling_articles(q)]
    except Exception:
        pass
    return jsonify({
        'query': q,
        'source_count': len(sources),
        'context_length': len(ctx),
        'sources': [
            {'type': s['type'], 'title': s['title'], 'key': s.get('key', '')}
            for s in sources
        ],
        'context_preview': ctx[:500],
        'fuling_matches': fuling_matches
    })


@app.route('/prescriptions')
@log_route
def prescriptions_page():
    if 'user' not in session:
        logger.warning("Prescriptions page access denied: not logged in")
        return redirect(url_for('login'))
    user = session.get('user')
    logger.info(f"Prescriptions page accessed by: {user}")
    return render_template('prescriptions.html', user=user)


@app.route('/api/prescriptions')
@log_route
def api_prescriptions():
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    user = session.get('user')
    prescriptions = db.get_prescriptions_for_user(user)
    logger.info(f"Prescriptions listed for {user}: {len(prescriptions)} found")
    return jsonify({'prescriptions': prescriptions})


@app.route('/api/prescriptions/<prescription_id>')
@log_route
def api_prescription_detail(prescription_id):
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    user = session.get('user')
    data = db.get_prescription(prescription_id)
    if data is None:
        logger.warning(f"Prescription not found: {prescription_id} by {user}")
        return jsonify({'error': 'Prescription not found'}), 404
    if data.get('user_email') != user and user != 'prof@tcm.org':
        logger.warning(f"Prescription access denied: {user} attempted to view {prescription_id}")
        return jsonify({'error': 'Access denied'}), 403
    logger.info(f"Prescription viewed: {prescription_id} by {user}")
    return jsonify(data)

def process_query(query, conversation_history=None):
    """Process user query using DeepSeek API with knowledge base context."""
    from chat_engine import ChatEngine
    
    if conversation_history is None:
        conversation_history = []
    
    logger.debug(f"process_query called with: {query[:100]}... | History: {len(conversation_history)} messages")

    if needs_formula_followup(query, conversation_history):
        logger.info("Formula recommendation request needs intake follow-up before processing")
        return formula_followup_response(query), [], "", []
    
    api_key = os.environ.get('DEEPSEEK_API_KEY')
    
    if not api_key:
        logger.warning("No DEEPSEEK_API_KEY found, using fallback responses")
        answer, sources, context = get_fallback_response(query)
        return answer, sources, context, []
    
    logger.info(f"Using DeepSeek API for query: {query[:50]}...")
    
    try:
        engine = ChatEngine(api_key)
        answer, sources, context, ai_formulas = engine.process_query(query, conversation_history)
        logger.info(f"DeepSeek query successful, answer length: {len(answer)} chars, context length: {len(context)} chars, ai_formulas: {len(ai_formulas)}")
        return answer, sources, context, ai_formulas
    except Exception as e:
        error_msg = str(e)
        logger.error(f"DeepSeek query failed: {error_msg}")
        
        if "timeout" in error_msg.lower() or "connection" in error_msg.lower():
            logger.warning("API timeout/connection error, falling back to basic responses")
            answer, sources, context = get_fallback_response(query)
            return answer, sources, context, []
        elif "Invalid API key" in error_msg:
            logger.error(f"API key error: {error_msg}")
            return (
                f"API key error: {error_msg}. Please check your DEEPSEEK_API_KEY.",
                [{"title": "Configuration Error", "type": "error", "key": "", "content": f"API key error: {error_msg}. Please check your DEEPSEEK_API_KEY."}],
                "",
                []
            )
        else:
            logger.warning(f"Unknown error, falling back: {error_msg}")
            answer, sources, context = get_fallback_response(query)
            return answer, sources, context, []


def get_fallback_response(query):
    """Get fallback response when API is not available."""
    query_lower = query.lower()
    
    if any(kw in query_lower for kw in ['ma huang', '麻黄', 'ephedra']):
        content = (
            "Ma Huang (Ephedra) is the chief herb in the classic formula Ma Huang Tang. "
            "It releases the exterior and promotes perspiration. The typical dosage is 6-10g. "
            "It is indicated for exterior cold with wheezing and absence of sweating."
        )
        return (
            content,
            [{"title": "Shang Han Lun - Chapter 3 (Ma Huang Tang)", "type": "fallback", "key": "", "content": content}],
            ""
        )
    elif any(kw in query_lower for kw in ['gui zhi', '桂枝', 'cinnamon']):
        content = (
            "Gui Zhi (Cinnamon Twig) is the chief herb in Gui Zhi Tang. "
            "It releases the exterior and harmonizes ying and wei. "
            "The typical dosage is 6-10g. It is indicated for exterior cold with sweating."
        )
        return (
            content,
            [{"title": "Shang Han Lun - Chapter 2 (Gui Zhi Tang)", "type": "fallback", "key": "", "content": content}],
            ""
        )
    elif any(kw in query_lower for kw in ['formula', 'prescription', '方', 'tang']):
        content = (
            "The Shang Han Lun contains 112 classical formulas. "
            "Each formula has specific indications based on the pattern diagnosis. "
            "Common formulas include Gui Zhi Tang, Ma Huang Tang, Xiao Chai Hu Tang, and others. "
            "The formula selection depends on the stage and pattern of the disease."
        )
        return (
            content,
            [{"title": "Shang Han Lun - Complete Formula Compendium", "type": "fallback", "key": "", "content": content}],
            ""
        )
    elif any(kw in query_lower for kw in ['shang han lun', 'treatise', '伤寒论']):
        content = (
            "The Shang Han Lun (Treatise on Cold Damage) is a classical TCM text written by Zhang Zhongjing. "
            "It systematically presents 112 formulas organized by pattern diagnosis (六经辨证). "
            "The text is foundational for understanding exterior diseases and formula selection in TCM."
        )
        return (
            content,
            [{"title": "Shang Han Lun - Introduction", "type": "fallback", "key": "", "content": content}],
            ""
        )
    else:
        content = (
            "Thank you for your question. The Shang Han Lun is the foundational text for classical TCM formula prescribing. "
            "I can answer questions about specific formulas, their compositions, indications, and modifications. "
            "Please ask about a specific formula, herb, or concept."
        )
        return (
            content,
            [{"title": "Shang Han Lun - General Reference", "type": "fallback", "key": "", "content": content}],
            ""
        )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    print(f"Starting Shanghan-TCM Evidence v1 on {host}:{port}")
    app.run(debug=debug, host=host, port=port)
