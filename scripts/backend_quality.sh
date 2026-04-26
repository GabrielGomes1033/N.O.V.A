#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/scripts/common.sh"
PYTHON_BIN="$(resolve_python_bin "${ROOT_DIR}")"

require_python_bin "${PYTHON_BIN}"

echo "[1/4] Verificando sintaxe do backend..."
"${PYTHON_BIN}" -m compileall -q "${ROOT_DIR}/backend_python"

echo "[2/4] Verificando formatação do backend..."
cd "${ROOT_DIR}/backend_python"
"${PYTHON_BIN}" -m black --check .

echo "[3/4] Verificando tipos do backend..."
"${PYTHON_BIN}" -m mypy

echo "[4/4] Rodando testes do backend..."
PYTHONPATH=. "${PYTHON_BIN}" -m pytest tests -q

echo "OK: backend validado com sucesso."
