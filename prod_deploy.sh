#!/usr/bin/env bash
# Full production deployment helper for Shanghan-TCM.
#
# Default use:
#   ./prod_deploy.sh
#
# Include the local SQLite content database:
#   ./prod_deploy.sh --with-db
#
# Override connection details:
#   ./prod_deploy.sh --remote ec2-user@example.com --key ~/.ssh/key.pem

set -euo pipefail

APP_NAME="${APP_NAME:-shanghan-tcm}"
SERVICE="${SERVICE:-shanghan-tcm}"
REMOTE="${REMOTE:-ec2-user@ec2-3-232-158-116.compute-1.amazonaws.com}"
SSH_KEY="${SSH_KEY:-/home/elinzi/Downloads/Basecode.pem}"
INSTALL_DIR="${INSTALL_DIR:-/opt/shanghan-tcm}"
MIRROR_DIR="${MIRROR_DIR:-/home/ec2-user/deploy}"
WITH_DB=false
SKIP_DEPS=false
SKIP_RESTART=false

usage() {
    cat <<EOF
Usage: $0 [options]

Deploy the local Shanghan-TCM checkout to production over SSH.

Options:
  --with-db              Replace production src/data/shanghan.db from local copy.
                         The live DB is backed up first. Omit this for code-only deploys.
  --skip-deps            Do not run pip install -r src/requirements.txt.
  --skip-restart         Copy files but do not restart the systemd service.
  --remote <user@host>   SSH target. Default: $REMOTE
  --key <path>           SSH private key. Default: $SSH_KEY
  --install-dir <path>   Production app dir. Default: $INSTALL_DIR
  --mirror-dir <path>    Production deploy mirror dir. Default: $MIRROR_DIR
  --service <name>       systemd service name. Default: $SERVICE
  -h, --help             Show this help.

Environment overrides are also supported:
  REMOTE=... SSH_KEY=... INSTALL_DIR=... MIRROR_DIR=... SERVICE=... $0
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --with-db) WITH_DB=true; shift ;;
        --skip-deps) SKIP_DEPS=true; shift ;;
        --skip-restart) SKIP_RESTART=true; shift ;;
        --remote) REMOTE="$2"; shift 2 ;;
        --key) SSH_KEY="$2"; shift 2 ;;
        --install-dir) INSTALL_DIR="$2"; shift 2 ;;
        --mirror-dir) MIRROR_DIR="$2"; shift 2 ;;
        --service) SERVICE="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
    esac
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Missing required command: $1" >&2
        exit 1
    fi
}

require_cmd ssh
require_cmd scp
require_cmd tar
require_cmd python3

if [[ ! -f "$SSH_KEY" ]]; then
    echo "SSH key not found: $SSH_KEY" >&2
    exit 1
fi

if [[ ! -f "src/requirements.txt" ]]; then
    echo "Run this script from the repository root; src/requirements.txt was not found." >&2
    exit 1
fi

echo "== Local validation =="
python3 -m py_compile server.py src/*.py tools/*.py

if [[ "$WITH_DB" == true ]]; then
    python3 - <<'PY'
import sqlite3
path = "src/data/shanghan.db"
conn = sqlite3.connect(path)
result = conn.execute("PRAGMA integrity_check").fetchone()[0]
if result != "ok":
    raise SystemExit(f"{path} integrity check failed: {result}")
print(f"{path}: integrity ok")
PY
fi

STAMP="$(date +%Y%m%d%H%M%S)"
TMP_DIR="$(mktemp -d)"
ARCHIVE="$TMP_DIR/shanghan-release-$STAMP.tgz"
REMOTE_ARCHIVE="/tmp/shanghan-release-$STAMP.tgz"

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

echo "== Building release archive =="
TAR_EXCLUDES=(
    --exclude='__pycache__'
    --exclude='*.pyc'
    --exclude='src/logs'
    --exclude='src/data/ai_config.json'
    --exclude='src/data/conversations'
    --exclude='src/data/feedback'
    --exclude='src/data/lessons'
    --exclude='src/data/prescriptions'
)

if [[ "$WITH_DB" != true ]]; then
    TAR_EXCLUDES+=(--exclude='src/data/*.db')
fi

tar -czf "$ARCHIVE" "${TAR_EXCLUDES[@]}" \
    server.py src tools textbook.txt .env.example deploy.sh

echo "Archive: $ARCHIVE"
echo "Remote:  $REMOTE"
echo "Target:  $INSTALL_DIR"
echo "Mirror:  $MIRROR_DIR"
echo "DB:      $([[ "$WITH_DB" == true ]] && echo replace || echo preserve)"

echo "== Uploading release =="
scp -i "$SSH_KEY" -o BatchMode=yes "$ARCHIVE" "$REMOTE:$REMOTE_ARCHIVE"

echo "== Installing on production =="
ssh -i "$SSH_KEY" -o BatchMode=yes "$REMOTE" \
    "APP_NAME='$APP_NAME' SERVICE='$SERVICE' INSTALL_DIR='$INSTALL_DIR' MIRROR_DIR='$MIRROR_DIR' REMOTE_ARCHIVE='$REMOTE_ARCHIVE' WITH_DB='$WITH_DB' SKIP_DEPS='$SKIP_DEPS' SKIP_RESTART='$SKIP_RESTART' bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail

STAMP="$(date +%Y%m%d%H%M%S)"
EXTRACT_DIR="/tmp/shanghan-release-$STAMP"
REMOTE_USER="$(id -un)"

echo "Extracting $REMOTE_ARCHIVE ..."
rm -rf "$EXTRACT_DIR"
mkdir -p "$EXTRACT_DIR"
tar -xzf "$REMOTE_ARCHIVE" -C "$EXTRACT_DIR"

echo "Preparing directories ..."
sudo mkdir -p "$INSTALL_DIR" "$MIRROR_DIR"
sudo chown -R "$REMOTE_USER:$REMOTE_USER" "$INSTALL_DIR" "$MIRROR_DIR"
mkdir -p "$INSTALL_DIR/src/data" "$INSTALL_DIR/src/logs" "$MIRROR_DIR/src/data"

if [[ ! -f "$INSTALL_DIR/.env" ]]; then
    echo "Creating initial .env from .env.example; add API keys via SSH after deploy."
    cp "$EXTRACT_DIR/.env.example" "$INSTALL_DIR/.env"
    chmod 600 "$INSTALL_DIR/.env"
fi

if [[ "$WITH_DB" == true && -f "$INSTALL_DIR/src/data/shanghan.db" ]]; then
    DB_BACKUP="$INSTALL_DIR/src/data/shanghan.db.bak-$STAMP"
    echo "Backing up live DB to $DB_BACKUP"
    cp "$INSTALL_DIR/src/data/shanghan.db" "$DB_BACKUP"
fi

if [[ "$SKIP_RESTART" != true ]]; then
    echo "Stopping $SERVICE for file install ..."
    sudo systemctl stop "$SERVICE" 2>/dev/null || true
fi

echo "Copying application files ..."
cp -a "$EXTRACT_DIR/server.py" "$INSTALL_DIR/server.py"
cp -a "$EXTRACT_DIR/textbook.txt" "$INSTALL_DIR/textbook.txt"
cp -a "$EXTRACT_DIR/deploy.sh" "$INSTALL_DIR/deploy.sh"
cp -a "$EXTRACT_DIR/src/." "$INSTALL_DIR/src/"
cp -a "$EXTRACT_DIR/tools" "$INSTALL_DIR/"

echo "Updating deploy mirror ..."
cp -a "$EXTRACT_DIR/server.py" "$MIRROR_DIR/server.py"
cp -a "$EXTRACT_DIR/textbook.txt" "$MIRROR_DIR/textbook.txt"
cp -a "$EXTRACT_DIR/deploy.sh" "$MIRROR_DIR/deploy.sh"
cp -a "$EXTRACT_DIR/src/." "$MIRROR_DIR/src/"
cp -a "$EXTRACT_DIR/tools" "$MIRROR_DIR/"

if [[ "$WITH_DB" == true ]]; then
    echo "Installing local SQLite DB ..."
    cp "$EXTRACT_DIR/src/data/shanghan.db" "$INSTALL_DIR/src/data/shanghan.db"
    cp "$EXTRACT_DIR/src/data/shanghan.db" "$MIRROR_DIR/src/data/shanghan.db"
fi

if [[ -f "$EXTRACT_DIR/src/data/fuling_articles.json" ]]; then
    cp "$EXTRACT_DIR/src/data/fuling_articles.json" "$INSTALL_DIR/src/data/fuling_articles.json"
    cp "$EXTRACT_DIR/src/data/fuling_articles.json" "$MIRROR_DIR/src/data/fuling_articles.json"
fi

chmod 600 "$INSTALL_DIR/.env" || true

if [[ ! -d "$INSTALL_DIR/.venv" ]]; then
    echo "Creating virtualenv ..."
    python3 -m venv "$INSTALL_DIR/.venv"
fi

if [[ "$SKIP_DEPS" != true ]]; then
    echo "Installing Python dependencies ..."
    "$INSTALL_DIR/.venv/bin/pip" install --upgrade pip -q
    "$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/src/requirements.txt" -q
    "$INSTALL_DIR/.venv/bin/pip" install gunicorn -q
fi

echo "Writing systemd service ..."
cat <<UNIT | sudo tee "/etc/systemd/system/$SERVICE.service" >/dev/null
[Unit]
Description=Shanghan-TCM Evidence
After=network.target

[Service]
Type=simple
User=$REMOTE_USER
WorkingDirectory=$INSTALL_DIR/src
Environment="PATH=$INSTALL_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/.venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 --timeout 120 server:app
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE.service" >/dev/null

if [[ "$SKIP_RESTART" != true ]]; then
    echo "Starting $SERVICE ..."
    sudo systemctl start "$SERVICE"
    sleep 2
fi

echo "Verifying deployment ..."
sudo systemctl is-active "$SERVICE"
cd "$INSTALL_DIR"
"$INSTALL_DIR/.venv/bin/python" - <<'PY'
import sqlite3
conn = sqlite3.connect("src/data/shanghan.db")
print("db_integrity", conn.execute("PRAGMA integrity_check").fetchone()[0])
for table in ["shl_articles", "fuling_articles", "lessons"]:
    try:
        print(table, conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    except Exception as exc:
        print(table, type(exc).__name__)
PY

curl -fsS http://127.0.0.1:5000/ >/dev/null
curl -fsS http://127.0.0.1:5000/en >/dev/null
echo "Deployment complete."

rm -rf "$EXTRACT_DIR" "$REMOTE_ARCHIVE"
REMOTE_SCRIPT

echo "== Done =="
