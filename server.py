#!/usr/bin/env uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "flask>=3.0.0",
# ]
# ///

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os

app = Flask(__name__, template_folder='docs/templates')
app.secret_key = 'shanghan-tcm-secret-key'

MD_DIR = os.path.dirname(os.path.abspath(__file__))

PROFESSIONAL_USERS = {
    'prof@tcm.org': 'password123'
}

def get_md_files():
    files = []
    for f in os.listdir(MD_DIR):
        if f.endswith('.md'):
            files.append(f)
    return sorted(files)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login')
def login():
    if 'user' in session:
        return redirect(url_for('chat'))
    return render_template('login.html')

@app.route('/chat')
def chat():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('chat.html', user=session['user'])

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    email = data.get('email', '')
    password = data.get('password', '')
    
    if email in PROFESSIONAL_USERS and PROFESSIONAL_USERS[email] == password:
        session['user'] = email
        return jsonify({'success': True, 'redirect': url_for('chat')})
    return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.pop('user', None)
    return jsonify({'success': True})

@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.json
    message = data.get('message', '')
    
    # Placeholder for Q&A logic - will search Shang Han Lun knowledge base
    response = {
        'answer': f'Responding to: {message}',
        'sources': ['Shang Han Lun - Chapter 1']
    }
    
    return jsonify(response)

@app.route('/read/<filename>')
def read_file(filename):
    filepath = os.path.join(MD_DIR, filename)
    if os.path.exists(filepath) and filename.endswith('.md'):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'content': content})
    return jsonify({'error': 'File not found'}), 404

@app.route('/save/<filename>', methods=['POST'])
def save_file(filename):
    filepath = os.path.join(MD_DIR, filename)
    if filename.endswith('.md'):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(request.json.get('content', ''))
        return jsonify({'success': True})
    return jsonify({'error': 'Invalid file'}), 400

@app.route('/files')
def list_files():
    return jsonify(get_md_files())

if __name__ == '__main__':
    print(f"Serving Shanghan-TCM Evidence")
    app.run(debug=True, port=8000)
