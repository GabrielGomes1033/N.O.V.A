#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."

if [ -x "venv311/bin/python" ]; then
  exec venv311/bin/python backend_python/api_server.py --host 0.0.0.0 --port 8000
fi

exec python3 backend_python/api_server.py --host 0.0.0.0 --port 8000
