#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
cd frontend_flutter

if ! command -v pkg-config >/dev/null 2>&1; then
  echo "Dependência ausente: pkg-config"
  echo "Instale com: sudo apt install -y pkg-config"
  exit 1
fi

for pkg in gtk+-3.0 gstreamer-1.0 gstreamer-app-1.0 gstreamer-audio-1.0; do
  if ! pkg-config --exists "$pkg"; then
    echo "Dependência ausente: $pkg"
    echo "Instale com:"
    echo "  sudo apt update"
    echo "  sudo apt install -y libgtk-3-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev"
    exit 1
  fi
done

flutter run -d linux
