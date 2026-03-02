#!/usr/bin/env python3
"""Shanghan-TCM Evidence v1 Server"""

import os
import sys
import json
import hashlib
import time
import functools
import logging
import glob
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from logger import setup_logging, get_logger, log_request, log_error, log_user_action

log = setup_logging("shanghan", level=logging.DEBUG)
logger = get_logger("server")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
FEEDBACK_DIR = os.path.join(DATA_DIR, 'feedback')
CONVERSATIONS_DIR = os.path.join(DATA_DIR, 'conversations')

os.makedirs(FEEDBACK_DIR, exist_ok=True)
os.makedirs(CONVERSATIONS_DIR, exist_ok=True)

logger.info("=" * 60)
logger.info("Shanghan-TCM Evidence v1 Server Starting")
logger.info(f"Base Dir: {BASE_DIR}")
logger.info(f"Feedback Dir: {FEEDBACK_DIR}")
logger.info(f"Conversations Dir: {CONVERSATIONS_DIR}")
logger.info("=" * 60)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'shanghan-tcm-secret-key-v1')
logger.info("Flask app created")

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

def get_user_hash(email):
    return hashlib.sha256(email.encode()).hexdigest()[:8]

def save_conversation(session_id, messages, user_email):
    timestamp = datetime.now().strftime('%Y-%m-%d')
    filename = f"conversation_{session_id}_{timestamp}.json"
    filepath = os.path.join(CONVERSATIONS_DIR, filename)
    
    conversation_data = {
        'session_id': session_id,
        'user_email': user_email,
        'timestamp': datetime.now().isoformat(),
        'messages': messages
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(conversation_data, f, indent=2, ensure_ascii=False)

@app.route('/')
@log_route
def home():
    logger.info("Home page accessed")
    return render_template('home.html')

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
    return render_template('chat.html', user=session['user'])

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
        session['messages'] = []
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
    user = session.get('user')
    session_id = session.get('session_id')
    messages = session.get('messages', [])
    
    if user and session_id and messages:
        save_conversation(session_id, messages, user)
    
    session.pop('user', None)
    session.pop('session_id', None)
    session.pop('messages', None)
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
    
    session['messages'] = session.get('messages', [])
    
    conversation_history = session['messages'].copy()
    
    session['messages'].append({
        'role': 'user',
        'content': message,
        'timestamp': datetime.now().isoformat()
    })
    
    logger.debug(f"Processing query: {message[:50]}... | History: {len(conversation_history)} messages")
    answer, sources = process_query(message, conversation_history)
    logger.debug(f"Query processed, answer length: {len(answer)} chars, sources: {sources}")
    
    session['messages'].append({
        'role': 'assistant',
        'content': answer,
        'sources': sources,
        'timestamp': datetime.now().isoformat()
    })
    
    message_id = f"msg_{len(session['messages'])}"
    
    logger.info(f"Chat response sent to user: {user} | Msg ID: {message_id}")
    return jsonify({
        'answer': answer,
        'sources': sources,
        'message_id': message_id
    })

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
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    user_hash = get_user_hash(session['user'])
    filename = f"feedback_{timestamp}_{user_hash}.json"
    filepath = os.path.join(FEEDBACK_DIR, filename)
    
    feedback_data = {
        'message_id': message_id,
        'rating': rating,
        'feedback': feedback_text,
        'timestamp': datetime.now().isoformat(),
        'user_email': session['user']
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(feedback_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Feedback saved to: {filename}")
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
    conversation_files = glob.glob(os.path.join(CONVERSATIONS_DIR, '*.json'))
    conversations = []
    for filepath in conversation_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            conversations.append({
                'session_id': data.get('session_id'),
                'user_email': data.get('user_email'),
                'timestamp': data.get('timestamp'),
                'message_count': len(data.get('messages', []))
            })
    return jsonify({'conversations': conversations})

@app.route('/admin/api/conversation/<session_id>')
@log_route
@admin_required
def admin_conversation(session_id):
    conversation_files = glob.glob(os.path.join(CONVERSATIONS_DIR, f'*{session_id}*.json'))
    if not conversation_files:
        return jsonify({'error': 'Conversation not found'}), 404
    # pick the first match (should be only one)
    with open(conversation_files[0], 'r', encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data)

@app.route('/admin/api/feedback')
@log_route
@admin_required
def admin_feedback():
    feedback_files = glob.glob(os.path.join(FEEDBACK_DIR, '*.json'))
    feedbacks = []
    for filepath in feedback_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            feedbacks.append(data)
    return jsonify({'feedbacks': feedbacks})

def process_query(query, conversation_history=None):
    """Process user query using DeepSeek API with knowledge base context."""
    from chat_engine import ChatEngine
    
    if conversation_history is None:
        conversation_history = []
    
    logger.debug(f"process_query called with: {query[:100]}... | History: {len(conversation_history)} messages")
    
    api_key = os.environ.get('DEEPSEEK_API_KEY')
    
    if not api_key:
        logger.warning("No DEEPSEEK_API_KEY found, using fallback responses")
        return get_fallback_response(query)
    
    logger.info(f"Using DeepSeek API for query: {query[:50]}...")
    
    try:
        engine = ChatEngine(api_key)
        result = engine.process_query(query, conversation_history)
        logger.info(f"DeepSeek query successful, answer length: {len(result[0])} chars")
        return result
    except Exception as e:
        error_msg = str(e)
        logger.error(f"DeepSeek query failed: {error_msg}")
        
        if "timeout" in error_msg.lower() or "connection" in error_msg.lower():
            logger.warning("API timeout/connection error, falling back to basic responses")
            return get_fallback_response(query)
        elif "Invalid API key" in error_msg:
            logger.error(f"API key error: {error_msg}")
            return (
                f"API key error: {error_msg}. Please check your DEEPSEEK_API_KEY.",
                ["Configuration Error"]
            )
        else:
            logger.warning(f"Unknown error, falling back: {error_msg}")
            return get_fallback_response(query)


def get_fallback_response(query):
    """Get fallback response when API is not available."""
    query_lower = query.lower()
    
    if any(kw in query_lower for kw in ['ma huang', '麻黄', 'ephedra']):
        return (
            "Ma Huang (Ephedra) is the chief herb in the classic formula Ma Huang Tang. "
            "It releases the exterior and promotes perspiration. The typical dosage is 6-10g. "
            "It is indicated for exterior cold with wheezing and absence of sweating.",
            ["Shang Han Lun - Chapter 3 (Ma Huang Tang)"]
        )
    elif any(kw in query_lower for kw in ['gui zhi', '桂枝', 'cinnamon']):
        return (
            "Gui Zhi (Cinnamon Twig) is the chief herb in Gui Zhi Tang. "
            "It releases the exterior and harmonizes ying and wei. "
            "The typical dosage is 6-10g. It is indicated for exterior cold with sweating.",
            ["Shang Han Lun - Chapter 2 (Gui Zhi Tang)"]
        )
    elif any(kw in query_lower for kw in ['formula', 'prescription', '方', 'tang']):
        return (
            "The Shang Han Lun contains 112 classical formulas. "
            "Each formula has specific indications based on the pattern diagnosis. "
            "Common formulas include Gui Zhi Tang, Ma Huang Tang, Xiao Chai Hu Tang, and others. "
            "The formula selection depends on the stage and pattern of the disease.",
            ["Shang Han Lun - Complete Formula Compendium"]
        )
    elif any(kw in query_lower for kw in ['shang han lun', 'treatise', '伤寒论']):
        return (
            "The Shang Han Lun (Treatise on Cold Damage) is a classical TCM text written by Zhang Zhongjing. "
            "It systematically presents 112 formulas organized by pattern diagnosis (六经辨证). "
            "The text is foundational for understanding exterior diseases and formula selection in TCM.",
            ["Shang Han Lun - Introduction"]
        )
    else:
        return (
            "Thank you for your question. The Shang Han Lun is the foundational text for classical TCM formula prescribing. "
            "I can answer questions about specific formulas, their compositions, indications, and modifications. "
            "Please ask about a specific formula, herb, or concept.",
            ["Shang Han Lun - General Reference"]
        )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    print(f"Starting Shanghan-TCM Evidence v1 on {host}:{port}")
    app.run(debug=debug, host=host, port=port)
