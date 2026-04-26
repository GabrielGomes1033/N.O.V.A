# Backend (Python)

Origem real: `backend_python/`

## Rodar localmente
```bash
bash platforms/backend/run.sh
```

## Healthcheck
```bash
curl "http://127.0.0.1:${NOVA_API_PORT:-8000}/health"
```

Para subir a API em outra porta local:

```bash
export NOVA_API_PORT=8119
bash platforms/backend/run.sh
```

## Rodar com Docker Compose

Se o terminal ainda não carregou o ambiente do Docker rootless:

```bash
source ~/.bashrc
```

Da raiz do projeto:

```bash
docker compose up -d
docker compose ps
```

Ver logs:

```bash
docker compose logs -f nova-api
```

Parar o stack:

```bash
docker compose down
```

## Validação rápida

```bash
make quality
make full
```
