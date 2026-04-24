from __future__ import annotations

from datetime import datetime

try:
    from fastapi import APIRouter, Depends, Query
    from fastapi.responses import JSONResponse
except Exception:
    APIRouter = None
    Depends = None
    Query = None
    JSONResponse = None

from .dependencies import rate_limit, require_rbac, require_token
from core.agent_observability import listar_traces, resumo_traces
from core.agente import executar_agente, planejar_objetivo
from core.aprendizado_admin import (
    atualizar_aprendizado,
    exportar_aprendizado_json,
    listar_aprendizados,
    remover_aprendizado,
    salvar_aprendizado,
)
from core.assistente_plus import (
    adicionar_lembrete,
    consultar_clima,
    consultar_clima_por_coordenadas,
    cotacoes_financeiras,
    listar_lembretes,
)
from core.autonomia_runtime import solicitar_execucao_autonoma
from core.document_analysis import analisar_documento_base64
from core.help_center import ajuda_topicos
from core.jarvis_chat_bridge import jarvis_status_snapshot
from core.memoria import carregar_memoria_usuario, salvar_memoria_usuario
from core.memoria_assuntos import perfil_assuntos
from core.painel_admin import carregar_config_painel, listar_usuarios, atualizar_config_painel
from core.premium_memory import exportar_perfis as premium_exportar_perfis
from core.premium_memory import importar_perfis as premium_importar_perfis
from core.rag_local import consultar_rag, estatisticas_feedback_rag, registrar_feedback_rag
from core.telegram_envio import enviar_mensagem_telegram
from core.voz_neural_api import sintetizar_neural_base64
from integrations.maps_provider import search_places


def _json(payload: dict, status_code: int = 200):
    return JSONResponse(content=payload, status_code=status_code)


def _bool_ou_none(valor):
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, str):
        normalized = valor.strip().lower()
        if normalized in {"true", "1", "sim", "yes", "on"}:
            return True
        if normalized in {"false", "0", "nao", "não", "no", "off"}:
            return False
    return None


if APIRouter is not None:
    router = APIRouter(tags=["compat"], dependencies=[Depends(rate_limit(120))])

    @router.get("/jarvis/status")
    def jarvis_status() -> dict:
        return jarvis_status_snapshot()

    @router.get("/backup/export", dependencies=[Depends(require_token())])
    def backup_export() -> dict:
        return {
            "ok": True,
            "backup": {
                "memory": carregar_memoria_usuario(),
                "knowledge": listar_aprendizados(),
                "users": listar_usuarios(),
                "config": carregar_config_painel(),
                "premium_profiles": premium_exportar_perfis(),
            },
        }

    @router.post("/backup/restore", dependencies=[Depends(require_token())])
    def backup_restore(body: dict):
        backup = body.get("backup", {})
        memory = backup.get("memory", {}) if isinstance(backup, dict) else {}
        if not isinstance(memory, dict):
            return _json({"ok": False, "error": "invalid_backup"}, status_code=400)

        salvar_memoria_usuario(memory)
        if isinstance(backup, dict):
            if isinstance(backup.get("knowledge"), list):
                from core.aprendizado_admin import salvar_base_aprendizado

                salvar_base_aprendizado(backup.get("knowledge", []))
            if isinstance(backup.get("users"), list):
                from core.seguranca import salvar_json_seguro
                from core.painel_admin import ARQUIVO_USUARIOS

                salvar_json_seguro(ARQUIVO_USUARIOS, backup.get("users"))
            if isinstance(backup.get("config"), dict):
                atualizar_config_painel(**backup.get("config", {}))
            if isinstance(backup.get("premium_profiles"), dict):
                premium_importar_perfis(backup.get("premium_profiles"))
        return {"ok": True, "restored": True}

    @router.get("/knowledge")
    def knowledge_get() -> dict:
        return exportar_aprendizado_json()

    @router.post("/knowledge")
    def knowledge_post(body: dict):
        gatilho = str(body.get("gatilho", "")).strip()
        resposta = str(body.get("resposta", "")).strip()
        categoria = str(body.get("categoria", "geral")).strip() or "geral"
        if not gatilho or not resposta:
            return _json({"ok": False, "error": "invalid_payload"}, status_code=400)
        salvar_aprendizado(gatilho, resposta, categoria=categoria)
        return exportar_aprendizado_json()

    @router.put("/knowledge/{item_id}")
    def knowledge_put(item_id: str, body: dict):
        item = atualizar_aprendizado(
            item_id=item_id,
            gatilho=body.get("gatilho"),
            resposta=body.get("resposta"),
            categoria=body.get("categoria"),
            ativo=_bool_ou_none(body.get("ativo")),
        )
        if not item:
            return _json({"ok": False, "error": "knowledge_not_found"}, status_code=404)
        return {"ok": True, "item": item}

    @router.delete("/knowledge/{item_id}")
    def knowledge_delete(item_id: str):
        ok = remover_aprendizado(item_id)
        if not ok:
            return _json({"ok": False, "error": "knowledge_not_found"}, status_code=404)
        return {"ok": True, "removed": True, "items": listar_aprendizados()}

    @router.get("/memory/subjects")
    def memory_subjects(limit: int = Query(default=8, ge=1, le=100)) -> dict:
        return perfil_assuntos(limit=limit)

    @router.get("/help/topics")
    def help_topics() -> dict:
        return ajuda_topicos()

    @router.get("/observability/traces")
    def observability_traces(limit: int = Query(default=120, ge=1, le=500)) -> dict:
        return {"ok": True, "items": listar_traces(limit=limit)}

    @router.get("/observability/summary")
    def observability_summary(window: int = Query(default=200, ge=1, le=500)) -> dict:
        return {"ok": True, "summary": resumo_traces(janela=window)}

    @router.get("/market/quotes")
    def market_quotes() -> dict:
        quotes = cotacoes_financeiras()
        return {"ok": quotes.get("ok") is True, "quotes": quotes}

    @router.get("/weather/now")
    def weather_now(city: str = "") -> dict:
        return {"ok": True, "summary": consultar_clima(city.strip())}

    @router.get("/weather/by-coords")
    def weather_by_coords(lat: float = Query(...), lon: float = Query(...)):
        return {"ok": True, "summary": consultar_clima_por_coordenadas(lat, lon)}

    @router.get("/maps/search")
    def maps_search(
        q: str = Query(default=""),
        lat: float | None = Query(default=None),
        lon: float | None = Query(default=None),
    ):
        out = search_places(q.strip(), latitude=lat, longitude=lon, limit=3)
        status_code = 200 if out.get("ok") else 400
        return _json(out, status_code=status_code)

    @router.get("/reminders")
    def reminders_get() -> dict:
        items = listar_lembretes()
        return {"ok": True, "items": items, "total": len(items)}

    @router.post("/reminders")
    def reminders_post(body: dict):
        texto = str(body.get("text", "")).strip()
        quando = str(body.get("when", "")).strip()
        if not quando:
            return _json(
                {
                    "ok": False,
                    "error": "when_required",
                    "message": "Informe data/hora para o lembrete.",
                },
                status_code=400,
            )
        try:
            datetime.fromisoformat(quando.replace("Z", "+00:00"))
        except Exception:
            return _json(
                {
                    "ok": False,
                    "error": "when_invalid",
                    "message": "Formato de data/hora inválido.",
                },
                status_code=400,
            )
        out = adicionar_lembrete(texto, quando=quando)
        status_code = 200 if out.get("ok") else 400
        return _json(out, status_code=status_code)

    @router.get("/rag/feedback/stats", dependencies=[Depends(require_token())])
    def rag_feedback_stats() -> dict:
        return estatisticas_feedback_rag()

    @router.post("/rag/query")
    def rag_query(body: dict):
        pergunta = str(body.get("query", "")).strip()
        out = consultar_rag(pergunta)
        status_code = 200 if out.get("ok") else 400
        return _json({"ok": out.get("ok") is True, "result": out}, status_code=status_code)

    @router.post("/rag/feedback", dependencies=[Depends(require_token())])
    def rag_feedback(body: dict):
        pergunta = str(body.get("query", "")).strip()
        chunk_id = str(body.get("chunk_id", "")).strip()
        try:
            score = int(body.get("score", 1))
        except Exception:
            score = 1
        out = registrar_feedback_rag(pergunta, chunk_id, score=score)
        status_code = 200 if out.get("ok") else 400
        return _json(out, status_code=status_code)

    @router.post(
        "/documents/analyze",
        dependencies=[
            Depends(require_token()),
            Depends(require_rbac("admin", "operator", "analyst", error_detail="rbac_forbidden_documents")),
        ],
    )
    def documents_analyze(body: dict):
        filename = str(body.get("filename", "")).strip()
        content_b64 = str(body.get("content_base64", "")).strip()
        out = analisar_documento_base64(filename, content_b64, auto_learn=True)
        status_code = 200 if out.get("ok") else 400
        return _json(out, status_code=status_code)

    @router.post("/agent/plan", dependencies=[Depends(require_token())])
    def agent_plan(body: dict):
        objetivo = str(body.get("objective", "")).strip()
        if not objetivo:
            return _json({"ok": False, "error": "objective_required"}, status_code=400)
        plano = planejar_objetivo(objetivo, contexto={})
        steps = []
        needs_confirmation = False
        for item in plano:
            entry = {
                "action": getattr(item, "acao", ""),
                "description": getattr(item, "descricao", ""),
                "parameters": getattr(item, "parametros", {}),
                "sensitive": bool(getattr(item, "sensivel", False)),
            }
            if entry["sensitive"]:
                needs_confirmation = True
            steps.append(entry)
        return {
            "ok": True,
            "objective": objetivo,
            "plan": steps,
            "needs_confirmation": needs_confirmation,
        }

    @router.post("/agent/execute", dependencies=[Depends(require_token())])
    def agent_execute(body: dict):
        objetivo = str(body.get("objective", "")).strip()
        if not objetivo:
            return _json({"ok": False, "error": "objective_required"}, status_code=400)
        result = executar_agente(objetivo, contexto={})
        steps = []
        for item in (result.get("plano", []) or []):
            steps.append(
                {
                    "action": getattr(item, "acao", ""),
                    "description": getattr(item, "descricao", ""),
                    "parameters": getattr(item, "parametros", {}),
                    "status": getattr(item, "status", ""),
                    "output": getattr(item, "saida", ""),
                    "error": getattr(item, "erro", ""),
                    "sensitive": bool(getattr(item, "sensivel", False)),
                }
            )
        return {
            "ok": True,
            "message": result.get("mensagem", ""),
            "confirmation_pending": result.get("confirmacao_pendente"),
            "plan": steps,
        }

    @router.post(
        "/autonomy/task",
        dependencies=[
            Depends(require_token()),
            Depends(require_rbac("admin", "operator", error_detail="rbac_forbidden_task")),
        ],
    )
    def autonomy_task(body: dict):
        objetivo = str(body.get("objective", "")).strip()
        origem = str(body.get("source", "api")).strip() or "api"
        out = solicitar_execucao_autonoma(objetivo, origem=origem)
        status_code = 200 if out.get("ok") else 400
        return _json(out, status_code=status_code)

    @router.post("/telegram/send")
    def telegram_send(body: dict):
        mensagem = str(body.get("message", "")).strip()
        config = carregar_config_painel()
        if not config.get("telegram_ativo"):
            return _json({"ok": False, "error": "telegram_disabled"}, status_code=400)
        ok, msg = enviar_mensagem_telegram(
            token=str(config.get("telegram_token", "")),
            chat_id=str(config.get("telegram_chat_id", "")),
            mensagem=mensagem,
        )
        status_code = 200 if ok else 400
        return _json({"ok": ok, "message": msg}, status_code=status_code)

    @router.post("/voice/neural")
    def voice_neural(body: dict):
        texto = str(body.get("text", "")).strip()
        perfil = str(body.get("voice_profile", "feminina")).strip()
        out = sintetizar_neural_base64(texto, perfil=perfil)
        status_code = 200 if out.get("ok") else 400
        return _json(out, status_code=status_code)
else:
    router = None
