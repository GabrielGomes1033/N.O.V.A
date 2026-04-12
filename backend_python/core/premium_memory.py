from __future__ import annotations

from datetime import datetime
import re

from core.caminhos import pasta_dados_app
from core.seguranca import carregar_json_seguro, salvar_json_seguro


ARQUIVO_PREMIUM = pasta_dados_app() / "premium_profiles.json"


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _base_profile(user_id: str) -> dict:
    return {
        "user_id": user_id,
        "nome_exibicao": user_id,
        "preferencias": {
            "tom": "natural",
            "tamanho": "media",
            "areas": [],
        },
        "rotina": {
            "periodo_ativo": "manha",
            "janela_produtiva": "09:00-12:00",
        },
        "objetivos": [],
        "contexto": {
            "ultima_localizacao": "",
            "ultimo_dispositivo": "",
            "observacoes": [],
        },
        "updated_at": _agora(),
    }


def _db_padrao() -> dict:
    return {"version": 1, "profiles": {}}


def _load_db() -> dict:
    raw = carregar_json_seguro(ARQUIVO_PREMIUM, _db_padrao())
    if not isinstance(raw, dict):
        raw = _db_padrao()
    profiles = raw.get("profiles")
    if not isinstance(profiles, dict):
        raw["profiles"] = {}
    return raw


def _save_db(db: dict) -> None:
    salvar_json_seguro(ARQUIVO_PREMIUM, db)


def _clean_user_id(user_id: str) -> str:
    uid = (user_id or "").strip().lower()
    if not uid:
        return "default"
    uid = re.sub(r"[^a-z0-9_.@-]", "_", uid)
    return uid[:64] or "default"


def obter_perfil(user_id: str) -> dict:
    uid = _clean_user_id(user_id)
    db = _load_db()
    profiles = db.get("profiles", {})
    p = profiles.get(uid)
    if not isinstance(p, dict):
        p = _base_profile(uid)
        profiles[uid] = p
        db["profiles"] = profiles
        _save_db(db)
    return p


def atualizar_perfil(user_id: str, dados: dict) -> dict:
    uid = _clean_user_id(user_id)
    db = _load_db()
    profiles = db.get("profiles", {})
    atual = profiles.get(uid)
    if not isinstance(atual, dict):
        atual = _base_profile(uid)

    if isinstance(dados, dict):
        for k in ["nome_exibicao", "preferencias", "rotina", "objetivos", "contexto"]:
            if k in dados:
                atual[k] = dados[k]

    atual["updated_at"] = _agora()
    profiles[uid] = atual
    db["profiles"] = profiles
    _save_db(db)
    return atual


def aprender_de_mensagem(user_id: str, mensagem: str) -> dict:
    perfil = obter_perfil(user_id)
    texto = (mensagem or "").lower()

    areas = []
    mapa = {
        "programacao": ["python", "api", "codigo", "flutter", "backend", "frontend"],
        "ia": ["ia", "agente", "llm", "prompt", "modelo"],
        "financas": ["dolar", "bitcoin", "ethereum", "mercado", "invest"],
        "produtividade": ["lembrete", "agenda", "planejar", "rotina"],
    }
    for area, termos in mapa.items():
        if any(t in texto for t in termos):
            areas.append(area)

    pref = perfil.get("preferencias", {})
    pref_areas = pref.get("areas", [])
    if not isinstance(pref_areas, list):
        pref_areas = []
    for a in areas:
        if a not in pref_areas:
            pref_areas.append(a)
    pref["areas"] = pref_areas[:12]

    objetivos = perfil.get("objetivos", [])
    if not isinstance(objetivos, list):
        objetivos = []
    if any(w in texto for w in ["quero", "objetivo", "meta", "preciso"]):
        resumo = (mensagem or "").strip()
        if resumo:
            objetivos.append({"texto": resumo[:180], "quando": _agora()})

    contexto = perfil.get("contexto", {})
    notas = contexto.get("observacoes", [])
    if not isinstance(notas, list):
        notas = []
    if len(texto.split()) >= 8:
        notas.append((mensagem or "").strip()[:200])
    contexto["observacoes"] = notas[-20:]

    perfil["preferencias"] = pref
    perfil["objetivos"] = objetivos[-20:]
    perfil["contexto"] = contexto
    return atualizar_perfil(user_id, perfil)


def personalizar_resposta_por_contexto(user_id: str, resposta: str) -> str:
    perfil = obter_perfil(user_id)

    objetivo = ""
    objetivos = perfil.get("objetivos", [])
    if isinstance(objetivos, list) and objetivos:
        last = objetivos[-1]
        if isinstance(last, dict):
            objetivo = str(last.get("texto", "")).strip()

    resposta_limpa = (resposta or "").strip()
    base = resposta_limpa
    if objetivo:
        base += f"\n\nContexto premium: sigo alinhada ao seu objetivo recente -> {objetivo[:120]}"
    return base


def exportar_perfis() -> dict:
    return _load_db()


def importar_perfis(payload: dict) -> bool:
    if not isinstance(payload, dict):
        return False
    profiles = payload.get("profiles")
    if not isinstance(profiles, dict):
        return False
    db = _db_padrao()
    db["profiles"] = profiles
    _save_db(db)
    return True
