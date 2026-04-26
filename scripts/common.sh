#!/usr/bin/env bash

resolve_python_bin() {
  local root_dir="$1"
  local python_bin="${NOVA_PYTHON_BIN:-}"

  if [[ -n "${python_bin}" ]]; then
    if [[ "${python_bin}" != /* && "${python_bin}" == */* && -x "${root_dir}/${python_bin}" ]]; then
      python_bin="${root_dir}/${python_bin}"
    fi
  elif [[ -x "${root_dir}/venv311/bin/python" ]]; then
    python_bin="${root_dir}/venv311/bin/python"
  elif [[ -x "${root_dir}/.venv/bin/python" ]]; then
    python_bin="${root_dir}/.venv/bin/python"
  else
    python_bin="python3"
  fi

  printf '%s\n' "${python_bin}"
}

default_api_port() {
  local default_port="${1:-8000}"
  local port="${NOVA_API_PORT:-${PORT:-${default_port}}}"

  if [[ "${port}" =~ ^[0-9]+$ ]] && (( port >= 1 && port <= 65535 )); then
    printf '%s\n' "${port}"
    return 0
  fi

  printf '%s\n' "${default_port}"
}

require_python_bin() {
  local python_bin="$1"

  if [[ -x "${python_bin}" ]]; then
    return 0
  fi

  if command -v "${python_bin}" >/dev/null 2>&1; then
    return 0
  fi

  echo "Python inválido: ${python_bin}" >&2
  return 1
}

resolve_api_token() {
  if [[ -n "${NOVA_API_TOKEN:-}" ]]; then
    printf '%s\n' "${NOVA_API_TOKEN}"
    return 0
  fi

  if [[ -n "${NOVA_API_TOKENS:-}" ]]; then
    printf '%s\n' "${NOVA_API_TOKENS}" | cut -d',' -f1 | xargs
    return 0
  fi

  return 1
}
