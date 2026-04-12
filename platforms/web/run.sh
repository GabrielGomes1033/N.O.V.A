#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
cd frontend_flutter

API_URL="${NOVA_API_URL:-}"
if [ -n "$API_URL" ]; then
  echo "Usando NOVA_API_URL=$API_URL"
  flutter run -d web-server --web-hostname 0.0.0.0 --web-port 8080 \
    --dart-define=NOVA_API_URL="$API_URL"
else
  flutter run -d web-server --web-hostname 0.0.0.0 --web-port 8080
fi
