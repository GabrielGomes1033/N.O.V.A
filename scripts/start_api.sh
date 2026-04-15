#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env.nova"
HOST="${NOVA_API_HOST:-0.0.0.0}"
PORT="${NOVA_API_PORT:-8000}"

show_help() {
  echo "Uso: scripts/start_api.sh [--env ARQUIVO] [--host HOST] [--port PORT]"
  echo
  echo "Exemplos:"
  echo "  scripts/start_api.sh"
  echo "  scripts/start_api.sh --env .env.nova --port 8080"
  echo
  echo "Ordem de carga:"
  echo "  1) Variáveis já exportadas no shell"
  echo "  2) Arquivo --env (ou .env.nova por padrão), se existir"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)
      ENV_FILE="$2"
      shift 2
      ;;
    --host)
      HOST="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    *)
      echo "Argumento inválido: $1"
      echo "Use --help para ver as opções."
      exit 1
      ;;
  esac
done

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
  echo "Arquivo de ambiente carregado: ${ENV_FILE}"
else
  echo "Arquivo de ambiente não encontrado (${ENV_FILE}). Seguindo com variáveis atuais do shell."
fi

if [[ -n "${NOVA_BRAVE_API_KEY:-}" ]]; then
  SEARCH_PROVIDER="Brave Search API"
elif [[ -n "${NOVA_SERPAPI_KEY:-}" || -n "${SERPAPI_API_KEY:-}" || -n "${SERPAPI_KEY:-}" ]]; then
  SEARCH_PROVIDER="SerpAPI"
else
  SEARCH_PROVIDER="fallback (Bing RSS + DuckDuckGo)"
fi

echo "Subindo NOVA API em http://${HOST}:${PORT}"
echo "Provider de busca principal: ${SEARCH_PROVIDER}"

cd "${ROOT_DIR}"
exec python3 backend_python/api_server.py --host "${HOST}" --port "${PORT}"
