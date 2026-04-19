# NOVA Frontend Flutter

Frontend principal da NOVA para Android, Web e desktop.

## Como a URL da API e resolvida

O app tenta descobrir o backend nesta ordem:

1. URL salva localmente nas configuracoes do app (`Conexao com API`)
2. `--dart-define=NOVA_API_URL=...`
3. Auto-detect por plataforma
4. Fallback automatico entre candidatos locais compativeis, quando nao existe URL manual definida

Defaults atuais:

- Android emulador: `http://10.0.2.2:8000`
- Linux, Windows, macOS e iOS simulator: `http://127.0.0.1:8000`
- Web local: `http://HOST_ATUAL:8000`

Na inicializacao o app testa `/health` para encontrar um backend valido antes de carregar os paineis principais.

Se estiver usando celular fisico, o caminho mais confiavel e informar o IP da maquina onde o backend roda, por exemplo `http://192.168.0.25:8000`.

## Subir o backend

Na raiz do projeto:

```bash
scripts/start_api.sh
```

Por padrao a API sobe em `http://0.0.0.0:8000`.

## Rodar o Flutter

```bash
cd frontend_flutter
flutter pub get
flutter run --dart-define=NOVA_API_URL=http://192.168.0.25:8000
```

Tambem e possivel abrir o app e definir a URL manualmente em `Configuracoes > Conexao com API`.

## Checks uteis

```bash
flutter analyze
flutter test
```
