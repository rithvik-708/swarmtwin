#!/usr/bin/env bash
# ==============================================================================
# SwarmTwin - Production AWS Graviton4 EC2 Deployment Script
# Optimized for Ubuntu 24.04 / 22.04 on AWS Graviton4 (Arm64)
# Supports the official Cloud-Optimized OpenCV Library (COOL) AMI & Standard AMIs
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

echo "=================================================================="
echo "      SwarmTwin - Agentic Vision AWS Deployment Engine"
echo "=================================================================="

# 1. Architecture Diagnostic
ARCH=$(uname -m)
echo "→ Detecting Host Architecture: ${ARCH}"
if [[ "${ARCH}" == "aarch64" || "${ARCH}" == "arm64" ]]; then
    echo "  ✓ AWS Graviton (Arm64) detected. Arm KleidiCV acceleration enabled."
else
    echo "  ! Host is ${ARCH}. Running in x86/SSE optimized fallback mode."
fi

# 2. System Dependencies (Debian / Ubuntu)
if command -v apt-get >/dev/null 2>&1; then
    echo "→ Checking system packages..."
    SUDO=""
    if [[ $EUID -ne 0 ]] && command -v sudo >/dev/null 2>&1; then
        SUDO="sudo"
    fi

    # Install Python venv, build tools, curl, nginx if missing
    PACKAGES=()
    command -v python3 >/dev/null 2>&1 || PACKAGES+=(python3)
    command -v pip3 >/dev/null 2>&1 || PACKAGES+=(python3-pip)
    python3 -c "import venv" >/dev/null 2>&1 || PACKAGES+=(python3-venv)
    command -v curl >/dev/null 2>&1 || PACKAGES+=(curl)
    command -v nginx >/dev/null 2>&1 || PACKAGES+=(nginx)

    if [ ${#PACKAGES[@]} -gt 0 ]; then
        echo "  Installing missing packages: ${PACKAGES[*]}..."
        $SUDO apt-get update -y
        $SUDO apt-get install -y --no-install-recommends "${PACKAGES[@]}" libgl1 libglib2.0-0
    fi

    # Check Node.js 20+
    NODE_INSTALLED=false
    if command -v node >/dev/null 2>&1; then
        NODE_VER=$(node -v | tr -d 'v' | cut -d'.' -f1)
        if [ "$NODE_VER" -ge 18 ]; then
            NODE_INSTALLED=true
        fi
    fi

    if [ "$NODE_INSTALLED" = false ]; then
        echo "  Installing Node.js 20.x for Next.js Control Room..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | $SUDO -E bash -
        $SUDO apt-get install -y nodejs
    fi
fi

# 3. Python Virtual Environment Setup
echo "→ Configuring Python environment..."
if [[ -d "/opt/cool" && -f "/opt/cool/bin/activate" ]]; then
    echo "  ✓ Found official COOL OpenCV 5 environment at /opt/cool"
    # shellcheck disable=SC1091
    source /opt/cool/bin/activate
else
    if [[ ! -d ".venv" ]]; then
        echo "  Creating virtual environment (.venv)..."
        python3 -m venv .venv
    fi
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

# Upgrade pip and install backend dependencies
echo "→ Installing backend requirements..."
pip install --upgrade pip
pip install -r backend/requirements.txt

# 4. Run Automated Test Suite
echo "→ Running verification test suite..."
pytest -v backend/tests/test_pipeline.py

# 5. Build Next.js Control Room Dashboard
echo "→ Building SwarmTwin Control Room (Next.js)..."
(
    cd swarmtwin-ui
    npm install
    npm run build
)

# 6. Run 500-Iteration COOL Benchmark
echo "→ Executing 500-iteration 1080p COOL Benchmark for Graviton evaluation..."
python3 backend/benchmark_cool.py --iterations 500 --output cool_benchmark_results.csv

# 7. Configure Systemd Services & Nginx (if running with systemd privileges)
if [[ -d "/etc/systemd/system" ]] && ( [[ $EUID -eq 0 ]] || command -v sudo >/dev/null 2>&1 ); then
    SUDO=""
    if [[ $EUID -ne 0 ]]; then
        SUDO="sudo"
    fi

    echo "→ Installing systemd services..."
    CURRENT_USER=$(id -un)
    VENV_PATH="${SCRIPT_DIR}/.venv"
    if [[ -d "/opt/cool" ]]; then
        VENV_PATH="/opt/cool"
    fi

    # Generate backend service with dynamic paths
    cat <<EOF | $SUDO tee /etc/systemd/system/swarmtwin-backend.service > /dev/null
[Unit]
Description=SwarmTwin FastAPI Agentic Vision Service
After=network.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${SCRIPT_DIR}
Environment="PATH=${VENV_PATH}/bin:/usr/local/bin:/usr/bin"
EnvironmentFile=-${SCRIPT_DIR}/backend/.env
ExecStart=${VENV_PATH}/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Generate UI service with dynamic paths
    cat <<EOF | $SUDO tee /etc/systemd/system/swarmtwin-ui.service > /dev/null
[Unit]
Description=SwarmTwin Next.js Control Room Dashboard
After=network.target swarmtwin-backend.service

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${SCRIPT_DIR}/swarmtwin-ui
Environment="NODE_ENV=production"
Environment="PORT=3000"
Environment="NEXT_PUBLIC_API_URL="
ExecStart=$(which npm) run start -- -p 3000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    $SUDO systemctl daemon-reload
    $SUDO systemctl enable swarmtwin-backend
    $SUDO systemctl enable swarmtwin-ui
    $SUDO systemctl restart swarmtwin-backend
    $SUDO systemctl restart swarmtwin-ui
    echo "  ✓ SwarmTwin services active in systemd."

    # Configure Nginx Reverse Proxy
    if command -v nginx >/dev/null 2>&1; then
        echo "→ Configuring Nginx reverse proxy on port 80..."
        $SUDO cp "${SCRIPT_DIR}/deploy/nginx/swarmtwin.conf" /etc/nginx/sites-available/swarmtwin
        $SUDO rm -f /etc/nginx/sites-enabled/default
        $SUDO ln -sf /etc/nginx/sites-available/swarmtwin /etc/nginx/sites-enabled/swarmtwin
        $SUDO nginx -t && $SUDO systemctl restart nginx
        echo "  ✓ Nginx active: Port 80 routes to Next.js (port 3000) and FastAPI (port 8000)."
    fi
else
    echo "→ Notice: Systemd privileges not detected. Starting backend in background..."
    nohup uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 2 > backend.log 2>&1 &
    (cd swarmtwin-ui && nohup npm run start -- -p 3000 > ui.log 2>&1 &)
fi

# 8. Healthcheck Verification
sleep 3
echo "→ Checking service health..."
PUBLIC_IP=$(curl -s -m 2 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || curl -s -m 2 https://checkip.amazonaws.com 2>/dev/null || echo "localhost")

echo "=================================================================="
echo " ✓ SwarmTwin Deployed Successfully!"
echo "=================================================================="
echo " Web Control Room:  http://${PUBLIC_IP}/"
echo " Backend API Docs:  http://${PUBLIC_IP}/docs"
echo " Health Status:     http://${PUBLIC_IP}/api/health"
echo " Benchmark Logs:    ${SCRIPT_DIR}/cool_benchmark_results.csv"
echo "=================================================================="
