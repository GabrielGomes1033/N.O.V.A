# Fluxo rápido (organizado)

## 1) Dia a dia (rápido)
Rode da raiz do projeto:

```bash
make quick
```

Isso valida:
- Backend: compilação Python
- Frontend: `flutter analyze`

## 2) Antes de publicar (completo)

```bash
make full
```

Executa checagem de integração completa (backend + frontend + smoke de API).

## 3) Build e instalação no celular

```bash
make apk API_URL=https://sua-api
```

## 4) Quando usar cada um
- `make quick`: durante desenvolvimento (várias vezes ao dia).
- `make quick-tests`: quando mexer em UI/estado e quiser confiança extra.
- `make full`: antes de merge/release.
