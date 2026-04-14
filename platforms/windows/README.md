# Windows Build (EXE)

Este projeto agora gera executável Windows por GitHub Actions.

## Artefatos gerados
- `nova-frontend-windows.zip` (app Flutter para Windows)
- `nova-backend.exe` (backend Python empacotado com PyInstaller)

## Como gerar
1. Suba o código para `main`.
2. No GitHub, abra `Actions` -> `windows-release`.
3. Clique em `Run workflow`.
4. Ao finalizar, baixe os artefatos da execução.

## Observação
- O frontend exige que o backend esteja acessível na URL configurada via:
  - `--dart-define=NOVA_API_URL=https://sua-api.exemplo.com`
