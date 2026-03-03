# Nginx Configuration for Shanghan-TCM v1

Nginx acts as a reverse proxy with SSL termination for the Flask application.

## Configuration Files

- `nginx.conf` - Main nginx configuration
- `generate-ssl.sh` - Script to generate self-signed SSL certificates for testing

## Setup Instructions

### 1. Install nginx

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install nginx
```

**macOS (Homebrew):**
```bash
brew install nginx
```

### 2. Generate SSL Certificates

For production, use certificates from a trusted CA (Let's Encrypt, etc.).

For development/testing, generate self-signed certificates:

```bash
# Make script executable
chmod +x generate-ssl.sh

# Generate certificates (requires openssl)
./generate-ssl.sh
```

This creates:
- `/etc/ssl/certs/shanghan-tcm.crt`
- `/etc/ssl/private/shanghan-tcm.key`

### 3. Configure nginx

Copy the nginx configuration to the appropriate location:

```bash
# Backup existing default config
sudo mv /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup

# Copy our config
sudo cp nginx.conf /etc/nginx/nginx.conf

# Test configuration
sudo nginx -t
```

### 4. Start Services

#### Start Flask Application
```bash
cd /home/elinzi/Coding/shanghan/src
# Using virtual environment
.venv/bin/python server.py
# Or with environment variables
PORT=5000 FLASK_HOST=127.0.0.1 .venv/bin/python server.py
```

#### Start nginx
```bash
sudo systemctl start nginx
# Or if not using systemd
sudo nginx
```

### 5. Verify Setup

- Visit `http://localhost` (should redirect to `https://localhost`)
- Visit `https://localhost` (accept SSL warning in development)

## Architecture

```
Browser → HTTPS (443) → nginx → HTTP (5000) → Flask
```

### Port Configuration

- **Flask**: Runs on `127.0.0.1:5000` by default
- **nginx**: Listens on `0.0.0.0:80` (HTTP) and `0.0.0.0:443` (HTTPS)
- HTTP requests are automatically redirected to HTTPS

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `5000` | Flask application port |
| `FLASK_HOST` | `127.0.0.1` | Flask bind address |
| `FLASK_DEBUG` | `true` | Flask debug mode |

## Testing

Run nginx configuration tests:

```bash
cd /home/elinzi/Coding/shanghan/src
pytest tests/test_nginx.py -v
```

## Troubleshooting

### 1. nginx fails to start
- Check syntax: `sudo nginx -t`
- Check error log: `sudo tail -f /var/log/nginx/error.log`

### 2. SSL certificate errors
- Ensure certificates exist at paths specified in `nginx.conf`
- Check permissions: key should be readable by nginx user

### 3. Flask not reachable
- Verify Flask is running: `curl http://127.0.0.1:5000`
- Check firewall: `sudo ufw status`

### 4. Permission denied on SSL key
```bash
sudo chmod 644 /etc/ssl/private/shanghan-tcm.key
sudo chown root:www-data /etc/ssl/private/shanghan-tcm.key
```

## Production Considerations

1. **Use Let's Encrypt** for trusted certificates
2. **Enable HSTS** in nginx configuration
3. **Configure proper SSL ciphers** for security
4. **Set up monitoring** and logging
5. **Use process manager** (systemd, supervisord) for Flask
6. **Consider using Gunicorn** as WSGI server for better performance