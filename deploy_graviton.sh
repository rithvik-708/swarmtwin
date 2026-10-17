#!/usr/bin/env bash
# ==============================================================================
# SwarmTwin - AWS Graviton4 (c8g.large) EC2 Deployment Script
# Targeting the Cloud-Optimized OpenCV Library (COOL) Ubuntu Marketplace AMI
# ==============================================================================

set -euo pipefail

echo "=================================================================="
echo " Deploying SwarmTwin to AWS Graviton4 COOL Ubuntu AMI"
echo "=================================================================="

# 1. Verify architecture
ARCH=$(uname -m)
echo "Detected Host Architecture: ${ARCH}"
if [[ "${ARCH}" != "aarch64" && "${ARCH}" != "arm64" ]]; then
    echo "Warning: Expected aarch64 (Graviton), running on ${ARCH}."
fi

# 2. Check for pre-configured COOL virtual environment
if [[ -d "/opt/cool" ]]; then
    echo "✓ Found official COOL OpenCV 5 environment at /opt/cool"
    source /opt/cool/bin/activate
else
    echo "Notice: /opt/cool not found in standard path. Using system Python venv..."
    python3 -m venv .venv
    source .venv/bin/activate
fi

# 3. Install dependencies
echo "Installing backend dependencies..."
pip install --upgrade pip
pip install fastapi uvicorn boto3 pydantic python-multipart openai numpy opencv-python

# 4. Verify OpenCV version and KleidiCV acceleration
echo "Verifying OpenCV installation:"
python3 -c "import cv2; print(f'OpenCV Version: {cv2.__version__}')"

# 5. Generate benchmark data for the $1,000 COOL Prize submission
echo "Generating mandatory 100-frame 1080p benchmark CSV..."
python3 backend/benchmark_cool.py --iterations 100 --output cool_benchmark_results.csv
echo "✓ Benchmark results saved to cool_benchmark_results.csv"

# 6. Start the FastAPI server on port 8000
echo "Starting SwarmTwin API on port 8000..."
exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 2
