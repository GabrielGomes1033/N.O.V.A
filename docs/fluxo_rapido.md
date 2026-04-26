# Fluxo rápido (organizado)

## 1) Dia a dia (rápido)
Rode da raiz do projeto:

```bash
make quick
```

Isso valida:
- Backend: compilação Python
- Frontend: `dart format` (checagem)
- Frontend: `flutter analyze`

## 2) Backend com mais rigor

```bash
make quality
```

Executa:
- Backend: compilação Python
- Backend: `black --check`
- Backend: `mypy`
- Backend: `pytest`

## 3) Antes de publicar (completo)

```bash
make full
```

Executa checagem de integração completa (backend + frontend + smoke de API).

## 4) Subir backend com Docker

Em terminal novo, se necessário:

```bash
source ~/.bashrc
```

Da raiz do projeto:

```bash
docker compose up -d
docker compose ps
curl "http://127.0.0.1:${NOVA_API_PORT:-8000}/health"
```

Comandos úteis:

```bash
docker compose logs -f
docker compose down
```

Se quiser trocar a porta local do stack:

```bash
export NOVA_API_PORT=8119
docker compose up -d
```

## 5) Build e instalação no celular

```bash
make apk API_URL=https://sua-api
```

## 6) Quando usar cada um
- `make quick`: durante desenvolvimento (várias vezes ao dia).
- `make quality`: quando mexer no backend e quiser validar qualidade estática + testes.
- `make quick-tests`: quando mexer em UI/estado e quiser confiança extra.
- `make full`: antes de merge/release.
- `docker compose up -d`: quando quiser subir o backend local em container.
