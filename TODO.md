# Correção de Bugs Críticos - N.O.V.A Backend
Status: ✅ Steps 1-5 CONCLUÍDOS | ⏳ Step 6 PENDENTE

## ✅ 1. Criar/Atualizar TODO.md [CONCLUÍDO]
- Track progress dos fixes

## ✅ 2. Fix bare excepts em main.py & api_server.py [CONCLUÍDO]
- [✅] Substituir `except Exception: pass` remanescentes em `main.py` e `api_server.py`
- [✅] Reduzir `except:` genéricos no legado CLI de `main.py`
- [✅] Adicionar `structlog` para tracing (`backend_python/core/logger.py` + dependency em `requirements.txt`)

## ✅ 3. Remover duplicação api_server.py vs FastAPI [CONCLUÍDO]
- [✅] backend_python/api/routes_chat.py: Migrar/enhance com processar_mensagem completa
- [✅] New: backend_python/api/routes_admin.py: Migrar /admin/* (users, config, state)
- [✅] New: backend_python/api/routes_system.py: /system/status, /autonomy/*, /security/audit, /ops/status
- [✅] backend_python/api/app.py: Incluir novos routers; enhance /health
- [✅] backend_python/main.py: Deprecar start de api_server; rodar só FastAPI (uvicorn)
- [✅] backend_python/api_server.py: Adicionar warning de deprecação

## ✅ 4. Adicionar input validation (Pydantic) [CONCLUÍDO]
- [✅] backend_python/models/schemas.py: Adicionar LocationUpdateRequest, LocationReverseRequest, LocationResponse
- [✅] New: backend_python/api/routes_location.py: Router /location/* com Pydantic + lógica de api_server.py
- [✅] backend_python/api/app.py: Incluir location_router (prefix="/location")
- [✅] Test: `uvicorn` + `curl /location/update`, `/current`, `/docs`

## ✅ 5. Rate-limit OPTIONS + CI lint (black/mypy/pytest) [CONCLUÍDO]

### 5.1 Rate Limiting + CORS [✅ CONCLUÍDO]
- [✅] backend_python/models/schemas.py: Adicionar RateLimitError schema
- [✅] backend_python/api/app.py: Add CORSMiddleware + rate_limit dependency
- [✅] backend_python/api/routes_chat.py: Add rate limit (90/min)
- [✅] backend_python/api/routes_location.py: Add rate limit (120/min)
- [✅] backend_python/api/routes_actions.py: Add rate limit (120/min, /approve 60/min)
- [✅] backend_python/api/routes_memory.py: Add rate limit (120/min)
- [✅] backend_python/api/routes_voice.py: Add rate limit (120/min)
- [✅] backend_python/api/routes_admin.py: Add rate limit (30/min)
- [✅] backend_python/api/routes_system.py: Add rate limit (30/min)

### 5.2 Linting Configuration [✅ CONCLUÍDO]
- [✅] backend_python/requirements.txt: Add dev deps (black, mypy, pytest, pytest-asyncio, httpx)
- [✅] backend_python/pyproject.toml: Create with black/mypy/pytest config

### 5.3 CI Workflow + Tests [✅ CONCLUÍDO]
- [✅] .github/workflows/ci.yml: Workflow atualizado para `black --check`, `mypy` e `pytest`
- [✅] backend_python/tests/test_api.py: Smoke tests (`health`, rate limit `429`, CORS `OPTIONS`)

### 5.4 Finalizar [✅ CONCLUÍDO]
- [✅] Atualizar TODO.md marcar Step 5 ✅
- [✅] Teste local: `black`, `mypy`, `pytest`

## ⏳ 6. Testes & Deploy
- [ ] `pytest` + `docker-compose up`

**Progresso: 5/6 steps entregues (~92%)**
Próximo: validar o Step 6 com `docker-compose up`
