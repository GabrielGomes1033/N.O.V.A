#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
cd frontend_flutter

API_URL="${NOVA_API_URL:-}"
if [[ -z "${API_URL}" ]]; then
  echo "Falha: defina NOVA_API_URL para o build web release."
  echo "Exemplo: NOVA_API_URL=https://sua-api.exemplo.com bash platforms/web/build_release.sh"
  exit 1
fi
echo "Build web release com NOVA_API_URL=$API_URL"
flutter build web --release --dart-define=NOVA_API_URL="$API_URL"

echo "Artefatos em: frontend_flutter/build/web"
