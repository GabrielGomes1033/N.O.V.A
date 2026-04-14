#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONT_DIR="${ROOT_DIR}/frontend_flutter"
API_URL="${1:-${NOVA_API_URL:-}}"
APK_PATH="${FRONT_DIR}/build/app/outputs/flutter-apk/app-release.apk"

if [[ -z "${API_URL}" ]]; then
  echo "Falha: informe a URL da API."
  echo "Uso: scripts/build_and_install_apk.sh https://sua-api.exemplo.com"
  echo "Ou exporte NOVA_API_URL antes de executar."
  exit 1
fi

echo "[1/4] Flutter pub get..."
cd "${FRONT_DIR}"
flutter pub get

echo "[2/4] Gerando APK release..."
flutter build apk --release --dart-define="NOVA_API_URL=${API_URL}"

if [[ ! -f "${APK_PATH}" ]]; then
  echo "Falha: APK não encontrado em ${APK_PATH}"
  exit 1
fi

echo "[3/4] Verificando dispositivo ADB..."
if ! command -v adb >/dev/null 2>&1; then
  echo "Falha: adb não encontrado no PATH."
  exit 1
fi

if ! adb devices | sed -n '2,$p' | grep -Eq '[[:space:]]device$'; then
  echo "Falha: nenhum dispositivo detectado pelo adb."
  echo "Dica: ative depuração USB e autorize o computador no celular."
  exit 1
fi

echo "[4/4] Instalando APK no celular..."
adb install -r "${APK_PATH}"

echo "OK: APK gerado e instalado com sucesso."
echo "APK: ${APK_PATH}"
