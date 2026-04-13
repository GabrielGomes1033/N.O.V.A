#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${1:-8117}"
HOST="127.0.0.1"
BASE_URL="http://${HOST}:${PORT}"

cleanup() {
  if [[ -n "${API_PID:-}" ]]; then
    kill "${API_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "[1/7] Compilando backend..."
cd "${ROOT_DIR}"
python3 -m compileall -q backend_python

echo "[2/7] Analisando frontend..."
cd "${ROOT_DIR}/frontend_flutter"
flutter analyze

echo "[3/7] Rodando testes do frontend..."
flutter test

echo "[4/7] Subindo API local (${BASE_URL})..."
cd "${ROOT_DIR}"
python3 backend_python/api_server.py --host "${HOST}" --port "${PORT}" >/tmp/nova_api_integration.log 2>&1 &
API_PID=$!
sleep 2

echo "[5/7] Testando endpoints principais..."
curl -fsS "${BASE_URL}/health" >/dev/null
curl -fsS "${BASE_URL}/help/topics" >/dev/null
curl -fsS "${BASE_URL}/memory/subjects?limit=5" >/dev/null
curl -fsS "${BASE_URL}/ops/status" >/dev/null
curl -fsS "${BASE_URL}/security/session-audit/verify" >/dev/null

curl -fsS -X POST "${BASE_URL}/chat" \
  -H "Content-Type: application/json" \
  --data-binary '{"message":"/help"}' >/dev/null

DOC_B64="$(printf "Documento de teste com contrato, dólar e compliance." | base64 -w0)"
curl -fsS -X POST "${BASE_URL}/documents/analyze" \
  -H "Content-Type: application/json" \
  --data-binary "{\"filename\":\"teste_ci.txt\",\"content_base64\":\"${DOC_B64}\"}" >/dev/null

echo "[6/7] Validando logs da API..."
if grep -qi "traceback" /tmp/nova_api_integration.log; then
  echo "Falha: traceback encontrado em /tmp/nova_api_integration.log"
  exit 1
fi

echo "[7/7] Concluído com sucesso."
echo "OK: integração backend+frontend validada."
