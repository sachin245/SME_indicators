#!/bin/bash
# Restart the sme-indicators PM2 app with the workaround LD_LIBRARY_PATH
# pointing at the user-local OpenBLAS extracted from the .deb (no sudo).
set -e
cd ~/apps/sme-indicators

export LD_LIBRARY_PATH="/home/admin/.local/openblas/usr/lib/arm-linux-gnueabihf/openblas-pthread:/home/admin/.local/openblas/usr/lib/arm-linux-gnueabihf"

echo "---NUMPY TEST---"
./venv/bin/python -c "import numpy as np, pandas as pd, duckdb; print('numpy', np.__version__, 'pandas', pd.__version__, 'duckdb', duckdb.__version__)"

echo "---PM2 RESTART---"
export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh"
pm2 delete sme-indicators 2>/dev/null || true
pm2 start ecosystem.config.cjs
pm2 save
sleep 5

echo "---PM2 LIST---"
pm2 list

echo "---HEALTH---"
curl -sf http://localhost:6002/api/health && echo

echo "---DATA HEALTH---"
curl -s http://localhost:6002/api/health/data
echo

echo "---INDEX---"
curl -s http://localhost:6002/ | head -c 200
echo
