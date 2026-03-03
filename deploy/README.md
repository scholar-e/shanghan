# Deployment Scripts for Shanghan-TCM

This directory contains scripts to deploy the Shanghan-TCM Flask application with nginx reverse proxy and SSL termination.

## Scripts

1. **install-nginx.sh** - Installs nginx, Python, and system dependencies.
2. **generate-ssl.sh** - Generates self-signed SSL certificates for development.
3. **setup-app.sh** - Sets up the Flask application with virtual environment, gunicorn, and systemd service.
4. **configure-nginx.sh** - Configures nginx with the application's reverse proxy settings.
5. **deploy.sh** - Main deployment script that orchestrates all steps.

## Usage

### Quick Deployment (Development)

```bash
cd /path/to/shanghan
./deploy/deploy.sh --domain localhost
```

### Production Deployment

1. Update the domain name and installation directory:

```bash
./deploy/deploy.sh --domain your-domain.com --install-dir /opt/shanghan-tcm
```

2. Replace self-signed certificates with Let's Encrypt:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

3. Enable HSTS and adjust SSL settings in `/etc/nginx/nginx.conf`.

### Individual Steps

You can run individual scripts with the appropriate environment variables:

```bash
export DOMAIN=your-domain.com
export INSTALL_DIR=/opt/shanghan-tcm

./deploy/install-nginx.sh
./deploy/generate-ssl.sh
./deploy/setup-app.sh
./deploy/configure-nginx.sh
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DOMAIN` | `localhost` | Domain name for SSL certificate and nginx server_name |
| `INSTALL_DIR` | `/opt/shanghan-tcm` | Application installation directory |
| `APP_USER` | Current user | User to run the application service |
| `APP_GROUP` | Same as user | Group for the application service |

### Systemd Service

The application runs as a systemd service named `shanghan-tcm.service`.

- Start: `sudo systemctl start shanghan-tcm`
- Stop: `sudo systemctl stop shanghan-tcm`
- Status: `sudo systemctl status shanghan-tcm`
- Logs: `sudo journalctl -u shanghan-tcm -f`

### Nginx Configuration

Nginx is configured as a reverse proxy with SSL termination:

- HTTP (port 80) redirects to HTTPS (port 443)
- HTTPS proxy passes requests to gunicorn on `127.0.0.1:5000`
- Static files served directly from `$INSTALL_DIR/src/static/`
- Health check endpoint at `/health`

## Troubleshooting

### Nginx fails to start
- Check syntax: `sudo nginx -t`
- Check error log: `sudo tail -f /var/log/nginx/error.log`

### Application service fails
- Check logs: `sudo journalctl -u shanghan-tcm`
- Verify virtual environment: `ls $INSTALL_DIR/.venv`
- Verify gunicorn installation: `$INSTALL_DIR/.venv/bin/gunicorn --version`

### SSL certificate errors
- Ensure certificates exist at `/etc/ssl/certs/shanghan-tcm.crt` and `/etc/ssl/private/shanghan-tcm.key`
- Check permissions: key should be readable by nginx user (www-data or nginx group)

## Notes

- Self-signed certificates are for development only. Use Let's Encrypt for production.
- The deployment scripts assume Ubuntu/Debian. Adjust for other distributions.
- Firewall configuration (UFW) may need adjustment to allow HTTP/HTTPS traffic.