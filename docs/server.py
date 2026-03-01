#!/usr/bin/env uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "flask>=3.0.0",
# ]
# ///

from flask import Flask, render_template, request, jsonify
import os

app = Flask(__name__)

MD_DIR = os.path.dirname(os.path.abspath(__file__))

def get_md_files():
    files = []
    for f in os.listdir(MD_DIR):
        if f.endswith('.md'):
            files.append(f)
    return sorted(files)

@app.route('/')
def index():
    files = get_md_files()
    current_file = request.args.get('file', files[0] if files else '')
    return render_template('index.html', files=files, current_file=current_file)

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
    print(f"Serving markdown files from: {MD_DIR}")
    app.run(debug=True, port=8000)
