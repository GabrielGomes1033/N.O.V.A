#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
cd frontend_flutter
flutter run -d android
