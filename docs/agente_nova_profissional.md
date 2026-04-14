# NOVA Agente Profissional - Upgrade

Este upgrade adiciona:

- Orquestração por API com plano/execução:
  - `POST /agent/plan`
  - `POST /agent/execute`
- Observabilidade de execução:
  - `GET /observability/traces?limit=120`
  - `GET /observability/summary?window=200`
- RAG com feedback de relevância:
  - `POST /rag/feedback`
  - `GET /rag/feedback/stats`
- Hardening básico:
  - Rate limit por IP e rota
  - Token opcional para rotas sensíveis via `NOVA_API_TOKEN`

## Segurança por token

Se `NOVA_API_TOKEN` estiver definido no backend, rotas sensíveis exigem:

- `Authorization: Bearer <token>`
ou
- `X-API-Key: <token>`

Rotas sensíveis protegidas:

- `/admin/*`
- `/security/*`
- `/backup/*`
- `/automation/*`
- `/rag/index`
- `/rag/feedback`
- `/agent/*`

## Exemplos

### Planejar ação de agente

```bash
curl -X POST https://sua-api.exemplo.com/agent/plan \
  -H "Content-Type: application/json" \
  -d '{"objective":"planejar meu dia com foco em estudos de API e Flutter"}'
```

### Executar ação de agente

```bash
curl -X POST https://sua-api.exemplo.com/agent/execute \
  -H "Content-Type: application/json" \
  -d '{"objective":"pesquisar boas práticas de autenticação API e resumir"}'
```

### Enviar feedback do RAG

Use `chunk_id` retornado em `result.snippet_items`:

```bash
curl -X POST https://sua-api.exemplo.com/rag/feedback \
  -H "Content-Type: application/json" \
  -d '{"query":"como proteger API", "chunk_id":"abc123", "score":1}'
```

`score`:

- `1` = relevante
- `-1` = irrelevante
