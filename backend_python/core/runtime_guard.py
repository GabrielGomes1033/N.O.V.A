from __future__ import annotations

import os
import time
from typing import Tuple


_BUCKETS: dict[str, list[float]] = {}


def _limpeza_rapida(agora: float, window_s: int) -> None:
    limiar = agora - max(1, int(window_s))
    stale = []

    for key, ts in _BUCKETS.items():
        vivos = [x for x in ts if x >= limiar]

        if vivos:
            _BUCKETS[key] = vivos
        else:
            stale.append(key)

    for k in stale:
        _BUCKETS.pop(k, None)


def checar_rate_limit(
    *,
    chave: str,
    limite: int = 120,
    janela_s: int = 60,
) -> Tuple[bool, int]:
    agora = time.time()

    _limpeza_rapida(agora, janela_s)

    bucket = _BUCKETS.setdefault(chave, [])
    limiar = agora - max(1, int(janela_s))

    bucket[:] = [x for x in bucket if x >= limiar]

    if len(bucket) >= max(1, int(limite)):
        retry = int(max(1, janela_s - (agora - bucket[0])))
        return False, retry

    bucket.append(agora)
    return True, 0


def token_api_configurado() -> bool:
    return bool(_tokens_ativos())


def _tokens_ativos() -> list[str]:
    single = os.getenv("NOVA_API_TOKEN", "").strip()
    multi = os.getenv("NOVA_API_TOKENS", "").strip()

    tokens: list[str] = []

    if single:
        tokens.append(single)

    if multi:
        for raw in multi.split(","):
            val = raw.strip()
            if val and val not in tokens:
                tokens.append(val)

    return tokens


def validar_token(headers) -> bool:
    tokens = _tokens_ativos()

    # Correção crítica: falhar fechado se não houver token configurado
    if not tokens:
        return False

    auth = str(headers.get("Authorization", "") or "").strip()
    x_api = str(headers.get("X-API-Key", "") or "").strip()

    if auth.lower().startswith("bearer "):
        recebido = auth[7:].strip()
        if recebido in tokens:
            return True

    if x_api and x_api in tokens:
        return True

    return False
