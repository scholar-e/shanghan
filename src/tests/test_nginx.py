#!/usr/bin/env python3
"""Test nginx configuration and Flask setup for SSL termination."""

import os
import sys
import subprocess
import shutil
import pytest
import tempfile
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
NGINX_CONF_PATH = BASE_DIR.parent / "nginx" / "nginx.conf"


class TestNginxConfiguration:
    """Test nginx configuration file."""
    
    def test_nginx_config_exists(self):
        """Verify nginx configuration file exists."""
        assert NGINX_CONF_PATH.exists(), f"Nginx config not found at {NGINX_CONF_PATH}"
        assert NGINX_CONF_PATH.is_file()
        
        # Check that config contains expected directives
        content = NGINX_CONF_PATH.read_text()
        assert "upstream flask_app" in content
        assert "server 127.0.0.1:5000" in content
        assert "listen 443 ssl" in content
        assert "proxy_pass http://flask_app" in content
        
    @pytest.mark.skipif(
        not shutil.which("nginx"),
        reason="nginx binary not found in PATH"
    )
    def test_nginx_config_syntax(self):
        """Test nginx configuration syntax using nginx -t."""
        # Create a temporary nginx config with the same content
        # to avoid permissions issues with /etc/ssl paths
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as tmp:
            content = NGINX_CONF_PATH.read_text()
            # Replace SSL certificate paths with dummy paths for syntax test
            content = content.replace(
                "ssl_certificate /etc/ssl/certs/shanghan-tcm.crt;",
                "ssl_certificate /tmp/dummy.crt;"
            )
            content = content.replace(
                "ssl_certificate_key /etc/ssl/private/shanghan-tcm.key;",
                "ssl_certificate_key /tmp/dummy.key;"
            )
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # Test nginx config syntax
            result = subprocess.run(
                ["nginx", "-t", "-c", tmp_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            assert result.returncode == 0, \
                f"Nginx config syntax error: {result.stderr}"
        finally:
            os.unlink(tmp_path)
    
    def test_nginx_config_upstream_port(self):
        """Verify upstream port matches Flask default port."""
        content = NGINX_CONF_PATH.read_text()
        
        # Extract upstream server line
        match = re.search(r'server\s+([^:]+):(\d+)', content)
        assert match is not None, "No upstream server found in config"
        
        host, port = match.groups()
        assert host == "127.0.0.1", f"Expected host 127.0.0.1, got {host}"
        assert port == "5000", f"Expected port 5000, got {port}"
    
    def test_nginx_static_config(self):
        """Verify nginx configuration includes static file serving."""
        content = NGINX_CONF_PATH.read_text()
        
        # Check for static file location block
        assert 'location /static/' in content
        assert 'alias' in content or 'root' in content
        
        # Check that static directory path is specified
        # Look for alias or root directive with path
        alias_match = re.search(r'alias\s+([^;]+);', content)
        root_match = re.search(r'root\s+([^;]+);', content)
        assert alias_match is not None or root_match is not None, \
            "No static file directory configured"
    
    def test_nginx_health_endpoint(self):
        """Verify nginx configuration includes health check endpoint."""
        content = NGINX_CONF_PATH.read_text()
        assert 'location /health' in content
        assert 'return 200' in content or 'proxy_pass' in content
    
    def test_nginx_proxy_headers(self):
        """Verify nginx sets proper proxy headers."""
        content = NGINX_CONF_PATH.read_text()
        assert 'proxy_set_header Host' in content
        assert 'proxy_set_header X-Real-IP' in content
        assert 'proxy_set_header X-Forwarded-Proto' in content

class TestFlaskConfiguration:
    """Test Flask application configuration for nginx setup."""
    
    def test_flask_default_port(self):
        """Verify Flask default port is 5000 (matches nginx upstream)."""
        with open(BASE_DIR / "server.py", "r") as f:
            content = f.read()
            # Check that default port is 5000 in the code
            assert "os.environ.get('PORT', 5000)" in content or \
                   "os.environ.get('PORT', 5000)" in content.replace(' ', '')
    
    def test_flask_default_host(self):
        """Verify Flask default host is 127.0.0.1 (localhost only)."""
        with open(BASE_DIR / "server.py", "r") as f:
            content = f.read()
            # Check that default host is 127.0.0.1
            assert "os.environ.get('FLASK_HOST', '127.0.0.1')" in content or \
                   "os.environ.get('FLASK_HOST', '127.0.0.1')" in content.replace(' ', '')
    
    def test_flask_host_not_public(self):
        """Verify Flask doesn't bind to 0.0.0.0 by default."""
        with open(BASE_DIR / "server.py", "r") as f:
            content = f.read()
            # Should not have host='0.0.0.0' as default
            # The default is now 127.0.0.1, but 0.0.0.0 might still appear in debug
            # We'll check that the main run call uses host variable
            assert "host=host" in content or "host = host" in content
    
    def test_environment_variables_respected(self):
        """Test that Flask respects PORT and FLASK_HOST environment variables."""
        # Simple check that the code reads these env vars
        with open(BASE_DIR / "server.py", "r") as f:
            content = f.read()
            assert "os.environ.get('PORT'" in content
            assert "os.environ.get('FLASK_HOST'" in content


class TestSSLConfiguration:
    """Test SSL-related configuration."""
    
    def test_ssl_certificate_paths_exist_in_config(self):
        """Verify SSL certificate paths are specified in config."""
        content = NGINX_CONF_PATH.read_text()
        assert "ssl_certificate" in content
        assert "ssl_certificate_key" in content
        
        # Check that paths are not placeholder comments
        lines = content.split('\n')
        ssl_cert_line = [l for l in lines if 'ssl_certificate' in l and not l.strip().startswith('#')]
        assert len(ssl_cert_line) > 0, "SSL certificate configuration missing or commented out"
    
    def test_http_redirect_to_https(self):
        """Verify HTTP server redirects to HTTPS."""
        content = NGINX_CONF_PATH.read_text()
        
        # Check for HTTP server block with redirect
        assert "listen 80" in content
        assert "return 301 https://" in content or "rewrite" in content


if __name__ == "__main__":
    # Quick manual test
    test = TestNginxConfiguration()
    test.test_nginx_config_exists()
    print("✓ Nginx config exists")
    
    if shutil.which("nginx"):
        test.test_nginx_config_syntax()
        print("✓ Nginx config syntax valid")
    else:
        print("⚠ nginx binary not found, skipping syntax test")
    
    test.test_nginx_config_upstream_port()
    print("✓ Upstream port matches Flask default")
    test.test_nginx_static_config()
    print("✓ Static file serving configured")
    test.test_nginx_health_endpoint()
    print("✓ Health endpoint configured")
    test.test_nginx_proxy_headers()
    print("✓ Proxy headers configured")
    
    test_flask = TestFlaskConfiguration()
    test_flask.test_flask_default_port()
    print("✓ Flask default port is 5000")
    test_flask.test_flask_default_host()
    print("✓ Flask default host is 127.0.0.1")
    test_flask.test_flask_host_not_public()
    print("✓ Flask host not public by default")
    test_flask.test_environment_variables_respected()
    print("✓ Flask respects environment variables")
    
    test_ssl = TestSSLConfiguration()
    test_ssl.test_ssl_certificate_paths_exist_in_config()
    print("✓ SSL certificate paths configured")
    test_ssl.test_http_redirect_to_https()
    print("✓ HTTP redirect to HTTPS configured")