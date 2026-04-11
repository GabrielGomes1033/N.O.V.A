# NOVA Sem Notebook (Deploy 24h + Backup Drive)

Este guia coloca o backend da NOVA na nuvem para o app funcionar sem depender do notebook ligado.

## 1) Subir backend no GitHub

No projeto:

```bash
git add .
git commit -m "deploy: backend nova em nuvem"
git push
```

## 2) Deploy no Render (Docker)

1. Acesse `https://render.com`
2. `New +` -> `Web Service`
3. Conecte seu repositório GitHub
4. Selecione pasta raiz do repo e configure:
   - **Root Directory**: `backend_python`
   - **Environment**: `Docker`
   - **Plan**: escolha um plano sempre ativo (para 24h real)
5. Adicione variáveis de ambiente (Environment):
   - `NOVA_ADMIN_USER`
   - `NOVA_ADMIN_PASSWORD`
6. Clique em Deploy

Quando subir, você terá uma URL como:
`https://sua-nova-api.onrender.com`

## 3) Testar API pública

No navegador:

```text
https://sua-nova-api.onrender.com/health
```

Esperado:

```json
{"ok": true, "service": "nova-api"}
```

## 4) Rodar app Flutter apontando para nuvem

```bash
cd /home/dev-0/Documentos/ChatBot/frontend_flutter
flutter pub get
flutter run --dart-define=NOVA_API_URL=https://sua-nova-api.onrender.com
```

## 5) Gerar APK final sem notebook

```bash
flutter build apk --release --dart-define=NOVA_API_URL=https://sua-nova-api.onrender.com
```

Instale o APK no celular. Depois disso, ele funciona sem precisar do notebook.

## 6) Backup secundário no Google Drive

Você pode habilitar backup remoto da memória da NOVA no Drive.

Variáveis no serviço backend:

- `GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON`:
  conteúdo JSON completo da service account (em uma linha)
  **ou**
- `GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE`:
  caminho do arquivo da credencial no servidor
- `NOVA_DRIVE_FOLDER_ID` (opcional): pasta no Drive
- `NOVA_DRIVE_FILE_NAME` (opcional): nome do arquivo de backup

Comandos após login admin:

```text
/admin drivebackup status
/admin drivebackup sincronizar
/admin drivebackup restaurar
```

## 7) Alternativa Google Cloud Run (oficial Google)

Você também pode publicar no Cloud Run:

```bash
gcloud run deploy nova-api \
  --source /home/dev-0/Documentos/ChatBot/backend_python \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars NOVA_ADMIN_USER=admin,NOVA_ADMIN_PASSWORD=senha_forte
```

Depois use a URL HTTPS gerada no Flutter `--dart-define=NOVA_API_URL=...`.

## 8) Importante para ficar 100% estável

- Use plano que não hiberna (free geralmente "dorme").
- Configure senha admin forte:
  - `/admin login ...`
  - `/admin configurar <usuario> <senha_forte>`
- Se quiser persistência forte de dados, use volume/disco persistente no provedor.
- Faça sincronização periódica do backup no Drive.
