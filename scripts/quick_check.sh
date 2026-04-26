#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/scripts/common.sh"
RUN_TESTS=0
PYTHON_BIN="$(resolve_python_bin "${ROOT_DIR}")"

for arg in "$@"; do
  case "$arg" in
    --tests)
      RUN_TESTS=1
      ;;
    -h|--help)
      echo "Uso: scripts/quick_check.sh [--tests]"
      echo "  --tests  Também roda testes do backend e flutter test."
      exit 0
      ;;
    *)
      echo "Argumento inválido: $arg"
      echo "Use --help para ver as opções."
      exit 1
      ;;
  esac
done

require_python_bin "${PYTHON_BIN}"

echo "[1/3] Compilando backend (rápido)..."
cd "${ROOT_DIR}"
"${PYTHON_BIN}" -m compileall -q backend_python

echo "[2/3] Verificando formatação do frontend..."
cd "${ROOT_DIR}/frontend_flutter"
dart format --output=none --set-exit-if-changed lib test

echo "[3/3] Analisando frontend..."
cd "${ROOT_DIR}/frontend_flutter"
flutter analyze

if [[ "${RUN_TESTS}" -eq 1 ]]; then
  echo "[extra 1/2] Rodando testes do backend..."
  cd "${ROOT_DIR}"
  "${PYTHON_BIN}" -m unittest discover -s backend_python/tests -q

  echo "[extra 2/2] Rodando testes do frontend..."
  cd "${ROOT_DIR}/frontend_flutter"
  flutter test
fi

echo "OK: quick check concluído."
