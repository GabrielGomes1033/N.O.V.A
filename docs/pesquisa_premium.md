# Pesquisa Premium (Internet Completa)

O backend agora suporta provedores premium de busca web para ampliar cobertura além de Wikipedia.

## Ordem de uso
1. `Brave Search API` (se chave estiver configurada)
2. `SerpAPI` (se chave estiver configurada)
3. `Bing RSS` (fallback)
4. `DuckDuckGo HTML` (fallback final)

## Variáveis de ambiente

Configure **uma** destas opções (ou as duas):

### Brave
- `NOVA_BRAVE_API_KEY`
- `BRAVE_SEARCH_API_KEY`
- `BRAVE_API_KEY`

### SerpAPI
- `NOVA_SERPAPI_KEY`
- `SERPAPI_API_KEY`
- `SERPAPI_KEY`

## Exemplo (Linux)

```bash
export NOVA_BRAVE_API_KEY="sua_chave_aqui"
python3 backend_python/api_server.py --host 0.0.0.0 --port 8000
```

## Start automático com `.env`

1. Crie seu arquivo local:

```bash
cp .env.nova.example .env.nova
```

2. Preencha sua chave no `.env.nova`.

3. Suba a API com carga automática:

```bash
scripts/start_api.sh
```

Você também pode mudar host/porta:

```bash
scripts/start_api.sh --host 0.0.0.0 --port 8080
```

## Resultado no chat

As respostas de pesquisa retornam:
- resumo consolidado
- `Fontes: ...`
- `Links: ...`
