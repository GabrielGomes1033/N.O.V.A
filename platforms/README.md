# NOVA - Estrutura por Plataforma

Esta pasta organiza o projeto por plataforma sem mover o código atual.

## Mapa
- `backend/`: API Python da assistente.
- `android/`: app Flutter Android.
- `ios/`: app Flutter iOS.
- `web/`: build e execução Flutter Web.
- `desktop/`: execução Flutter para Linux/Windows/macOS.
- `shared/`: documentação e padrões compartilhados.

## Código-fonte real
- Backend: `backend_python/`
- Frontend: `frontend_flutter/`

## Uso rápido
- Android: `bash platforms/android/run.sh`
- iOS: `bash platforms/ios/run.sh`
- Web: `bash platforms/web/run.sh`
- Desktop: `bash platforms/desktop/run.sh`
- Backend: `bash platforms/backend/run.sh`

- cd /home/dev-0/Documentos/ChatBot
  pkill -f "backend_python/api_server.py" || true
  bash platforms/backend/run.sh

-  cd /home/dev-0/Documentos/ChatBot
   pkill -f "flutter run -d web-server" || true
   bash platforms/web/run.sh

