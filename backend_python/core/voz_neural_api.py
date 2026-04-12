from __future__ import annotations

import asyncio
import base64
from pathlib import Path
import tempfile

from core.voz import preparar_texto_para_voz


VOZ_NEURAL_PADRAO = "pt-BR-FranciscaNeural"
VOZES_SUPORTADAS = {
    "francisca": "pt-BR-FranciscaNeural",
    "thalita": "pt-BR-ThalitaMultilingualNeural",
    "feminina": "pt-BR-FranciscaNeural",
}


def _resolver_voz(perfil: str) -> str:
    p = (perfil or "").strip().lower()
    return VOZES_SUPORTADAS.get(p, VOZ_NEURAL_PADRAO)


async def _salvar_edge_tts(texto: str, caminho_saida: str, voz: str) -> None:
    try:
        import edge_tts  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"edge_tts_nao_instalado: {exc}") from exc

    comunicador = edge_tts.Communicate(
        text=texto,
        voice=voz,
        rate="+8%",
        pitch="+2Hz",
    )
    await comunicador.save(caminho_saida)


def sintetizar_neural_base64(texto: str, perfil: str = "feminina") -> dict:
    texto_limpo = preparar_texto_para_voz(texto or "")
    if not texto_limpo:
        return {"ok": False, "error": "texto_vazio"}

    voz = _resolver_voz(perfil)
    try:
        with tempfile.NamedTemporaryFile(prefix="nova_tts_", suffix=".mp3", delete=False) as tmp:
            caminho = tmp.name
        asyncio.run(_salvar_edge_tts(texto_limpo[:900], caminho, voz))
        data = Path(caminho).read_bytes()
        Path(caminho).unlink(missing_ok=True)
        if not data:
            return {"ok": False, "error": "audio_vazio"}
        return {
            "ok": True,
            "audio_base64": base64.b64encode(data).decode("ascii"),
            "mime": "audio/mpeg",
            "voice": voz,
            "provider": "edge-tts",
        }
    except Exception as exc:
        return {"ok": False, "error": f"tts_neural_fail: {exc}"}
