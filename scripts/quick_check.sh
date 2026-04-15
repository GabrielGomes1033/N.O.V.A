#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_TESTS=0

for arg in "$@"; do
  case "$arg" in
    --tests)
      RUN_TESTS=1
      ;;
    -h|--help)
      echo "Uso: scripts/quick_check.sh [--tests]"
      echo "  --tests  Também roda flutter test."
      exit 0
      ;;
    *)
      echo "Argumento inválido: $arg"
      echo "Use --help para ver as opções."
      exit 1
      ;;
  esac
done

echo "[1/2] Compilando backend (rápido)..."
cd "${ROOT_DIR}"
python3 -m compileall -q backend_python

echo "[2/2] Analisando frontend..."
cd "${ROOT_DIR}/frontend_flutter"
flutter analyze

if [[ "${RUN_TESTS}" -eq 1 ]]; then
  echo "[extra] Rodando testes do frontend..."
  flutter test
fi

echo "OK: quick check concluído."
