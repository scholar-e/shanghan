#!/usr/bin/env python3
"""Shanghan-TCM Evidence v1 — self-contained entry point with optional SSL."""

import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))

# Auto-activate virtual environment if it exists
VENV_PYTHON = os.path.join(BASE, '.venv', 'bin', 'python3')
if os.path.isfile(VENV_PYTHON) and sys.executable != VENV_PYTHON:
    os.execve(VENV_PYTHON, [VENV_PYTHON] + sys.argv, os.environ)

# Ensure src/ is on the path so imports resolve
SRC = os.path.join(BASE, 'src')
for p in [SRC, BASE]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Load .env before importing the app
env_path = os.path.join(BASE, '.env')
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

from src.server import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'

    ssl_cert = os.environ.get('SSL_CERT_PATH')
    ssl_key = os.environ.get('SSL_KEY_PATH')

    ssl_context = None
    scheme = "http"
    if ssl_cert and ssl_key:
        if os.path.isfile(ssl_cert) and os.path.isfile(ssl_key):
            ssl_context = (ssl_cert, ssl_key)
            scheme = "https"
            print(f"SSL enabled: {ssl_cert}")
        else:
            print(f"Warning: SSL cert/key files not found at {ssl_cert}, {ssl_key}", file=sys.stderr)

    print(f"Starting Shanghan-TCM Evidence v1 on {scheme}://{host}:{port}")
    app.run(debug=debug, host=host, port=port, ssl_context=ssl_context)
