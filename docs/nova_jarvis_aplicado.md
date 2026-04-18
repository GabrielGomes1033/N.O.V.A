# NOVA JARVIS Aplicado

Este documento resume o que foi aplicado no projeto para aproximar a NOVA da arquitetura estilo JARVIS.

## Backend aplicado

- Orquestrador novo em `backend_python/core/orchestrator.py`
- Classificador de intenção em `backend_python/core/intent_classifier.py`
- Estilo de resposta JARVIS em `backend_python/core/response_style.py`
- Registry de ferramentas em `backend_python/core/tools_registry.py`
- Ponte de compatibilidade com chat legado em `backend_python/core/jarvis_chat_bridge.py`
- Memória SQLite em `backend_python/memory/sqlite_store.py`
- Perfil e memória semântica preparados em `backend_python/memory/profile_store.py` e `vector_store.py`
- Integrações base em `backend_python/integrations/`
- Segurança organizada em `backend_python/security/`
- Rotas FastAPI em `backend_python/api/`

## Endpoints novos

- `GET /jarvis/status`
- `GET /actions/tools`
- `POST /actions/approve`
- `GET /memory/recent`
- `GET /memory/search`
- `POST /memory`
- `GET /voice/status`

Esses endpoints existem tanto na base FastAPI nova quanto no `api_server.py` atual.

## Compatibilidade preservada

- O `/chat` antigo com `{"message": "..."}` continua funcionando.
- O `/chat` novo com `{"user_id": "...", "text": "...", "mode": "...", "auto_approve": false}` agora também funciona.
- O servidor legado ganhou confirmação de ação sensível no próprio chat para ferramentas do novo orquestrador.

## Flutter aplicado

- O app agora tenta primeiro o payload estruturado do novo `/chat` e faz fallback automático para o formato antigo.
- A rail lateral exibe estado do cérebro JARVIS, memória recente, tools disponíveis e fase de voz.
- O frontend já consulta os novos endpoints de status, memória, ações e voz.

## Próximas fases naturais

- Conectar STT/TTS real com OpenAI Audio API.
- Adicionar wake word contínua com runtime controlado.
- Transformar os cards laterais em dashboards editáveis de memória, automações e admin.
- Ligar as ferramentas novas a Notion, Calendar e Home Assistant com credenciais reais.
