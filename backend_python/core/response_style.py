from __future__ import annotations


SYSTEM_PROMPT = """
Voce e a NOVA, uma assistente pessoal e tecnica inspirada no estilo JARVIS.
Seja objetiva, inteligente, elegante e prestativa.
Fale com confianca, mas sem arrogancia.
Quando fizer sentido, antecipe o proximo passo util.
Nunca execute acoes criticas sem confirmacao explicita.
Use respostas curtas por padrao e expanda so quando necessario.
""".strip()


def _clean_text(text: str) -> str:
    return " ".join(str(text or "").strip().split())


def _truncate(text: str, limit: int) -> str:
    body = _clean_text(text)
    if len(body) <= limit:
        return body
    shortened = body[: max(40, limit)].rsplit(" ", 1)[0].strip()
    return (shortened or body[:limit]).rstrip(" ,.;:-") + "..."


def style_response(texto_base: str, modo: str = "normal") -> str:
    body = str(texto_base or "").strip()
    if not body:
        return ""

    modo_normalizado = str(modo or "normal").strip().lower() or "normal"
    if modo_normalizado == "compacto":
        return _truncate(body, 180)
    if modo_normalizado == "executivo":
        return f"Resumo executivo:\n{body}"
    if modo_normalizado == "tecnico":
        return f"Analise tecnica:\n{body}"
    if modo_normalizado == "estrategico":
        return f"Visao estrategica:\n{body}"
    return body
