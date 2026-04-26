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
  - Token obrigatório para rotas protegidas via `NOVA_API_TOKEN` ou `NOVA_API_TOKENS`

## Segurança por token

Para usar rotas protegidas, configure no backend:

- `NOVA_API_TOKEN=<token>`
ou
- `NOVA_API_TOKENS=<token1>,<token2>`

As chamadas autenticadas aceitam:

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
- `/ops/status`
- `/system/status`
- `/documents/analyze`

Sem token valido, essas rotas retornam `401 unauthorized`.

## Exemplos

### Planejar ação de agente

```bash
curl -X POST https://sua-api.exemplo.com/agent/plan \
  -H "X-API-Key: seu-token" \
  -H "Content-Type: application/json" \
  -d '{"objective":"planejar meu dia com foco em estudos de API e Flutter"}'
```

### Executar ação de agente

```bash
curl -X POST https://sua-api.exemplo.com/agent/execute \
  -H "Authorization: Bearer seu-token" \
  -H "Content-Type: application/json" \
  -d '{"objective":"pesquisar boas práticas de autenticação API e resumir"}'
```

### Enviar feedback do RAG

Use `chunk_id` retornado em `result.snippet_items`:

```bash
curl -X POST https://sua-api.exemplo.com/rag/feedback \
  -H "X-API-Key: seu-token" \
  -H "Content-Type: application/json" \
  -d '{"query":"como proteger API", "chunk_id":"abc123", "score":1}'
```

`score`:

- `1` = relevante
- `-1` = irrelevante
