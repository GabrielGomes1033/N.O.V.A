from __future__ import annotations

import requests


def enviar_mensagem_telegram(token: str, chat_id: str, mensagem: str, timeout: int = 10) -> tuple[bool, str]:
    token = (token or "").strip()
    chat_id = (chat_id or "").strip()
    mensagem = (mensagem or "").strip()

    if not token or not chat_id:
        return False, "Token e chat_id do Telegram não configurados."
    if not mensagem:
        return False, "Mensagem vazia."

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": mensagem,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=timeout,
        )
    except Exception as exc:
        return False, f"Falha de rede no Telegram: {exc}"

    if response.status_code < 200 or response.status_code >= 300:
        return False, f"Erro HTTP Telegram {response.status_code}."

    try:
        payload = response.json()
    except Exception:
        return False, "Resposta inválida da API do Telegram."

    if payload.get("ok") is not True:
        descricao = payload.get("description") or "erro_desconhecido"
        return False, f"Telegram rejeitou envio: {descricao}"

    return True, "Mensagem enviada para o Telegram."
