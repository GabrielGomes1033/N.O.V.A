#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/scripts/common.sh"
PORT="${1:-8117}"
HOST="127.0.0.1"
BASE_URL="http://${HOST}:${PORT}"
PYTHON_BIN="$(resolve_python_bin "${ROOT_DIR}")"
API_LOG="${API_LOG:-/tmp/nova_api_integration.log}"
SMOKE_API_TOKEN="$(resolve_api_token || true)"
if [[ -z "${SMOKE_API_TOKEN}" ]]; then
  SMOKE_API_TOKEN="nova-integration-smoke-token"
fi
AUTH_HEADERS=(-H "X-API-Key: ${SMOKE_API_TOKEN}")

cleanup() {
  if [[ -n "${API_PID:-}" ]]; then
    kill "${API_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

wait_for_api() {
  local attempts="${1:-20}"
  local delay_seconds="${2:-1}"

  for ((attempt = 1; attempt <= attempts; attempt++)); do
    if curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep "${delay_seconds}"
  done

  echo "Falha: API não respondeu em ${BASE_URL}/health após ${attempts} tentativas."
  echo "Log da integração: ${API_LOG}"
  return 1
}

require_python_bin "${PYTHON_BIN}"

echo "[1/8] Compilando backend..."
cd "${ROOT_DIR}"
"${PYTHON_BIN}" -m compileall -q backend_python

echo "[2/8] Rodando testes do backend..."
cd "${ROOT_DIR}/backend_python"
PYTHONPATH=. "${PYTHON_BIN}" -m pytest tests -q

echo "[3/8] Analisando frontend..."
cd "${ROOT_DIR}/frontend_flutter"
flutter analyze

echo "[4/8] Rodando testes do frontend..."
flutter test

echo "[5/8] Subindo API local (${BASE_URL})..."
cd "${ROOT_DIR}"
env NOVA_API_TOKEN="${SMOKE_API_TOKEN}" \
  "${PYTHON_BIN}" -m uvicorn backend_python.api.app:create_app --factory --host "${HOST}" --port "${PORT}" >"${API_LOG}" 2>&1 &
API_PID=$!
wait_for_api

echo "[6/8] Testando endpoints principais..."
curl -fsS "${BASE_URL}/help/topics" >/dev/null
curl -fsS "${BASE_URL}/memory/subjects?limit=5" >/dev/null
curl -fsS "${AUTH_HEADERS[@]}" "${BASE_URL}/ops/status" >/dev/null
curl -fsS "${AUTH_HEADERS[@]}" "${BASE_URL}/system/status" >/dev/null

curl -fsS -X POST "${BASE_URL}/chat" \
  -H "Content-Type: application/json" \
  --data-binary '{"message":"/help"}' >/dev/null

DOC_B64="$(printf "Documento de teste com contrato, dólar e compliance." | base64 -w0)"
curl -fsS -X POST "${BASE_URL}/documents/analyze" \
  "${AUTH_HEADERS[@]}" \
  -H "Content-Type: application/json" \
  --data-binary "{\"filename\":\"teste_ci.txt\",\"content_base64\":\"${DOC_B64}\"}" >/dev/null

echo "[7/8] Validando logs da API..."
if grep -qi "traceback" "${API_LOG}"; then
  echo "Falha: traceback encontrado em ${API_LOG}"
  exit 1
fi

echo "[8/8] Concluído com sucesso."
echo "OK: integração backend+frontend validada."
