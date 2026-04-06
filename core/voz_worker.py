from __future__ import annotations

import asyncio
from pathlib import Path
import subprocess
import sys
import time

import edge_tts


def gerar_nome_arquivo(pasta_cache: Path) -> Path:
    pasta_cache.mkdir(parents=True, exist_ok=True)
    return pasta_cache / f"nova_{int(time.time() * 1000)}.mp3"


async def gerar_audio(texto: str, arquivo_saida: Path, voz: str) -> None:
    comunicador = edge_tts.Communicate(
        texto,
        voice=voz,
        rate="-8%",
        pitch="+0Hz",
    )
    await comunicador.save(str(arquivo_saida))


def tocar_audio(player: str, arquivo_saida: Path) -> None:
    subprocess.run(
        [player, "-q", str(arquivo_saida)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def main() -> int:
    if len(sys.argv) < 5:
        return 1

    texto = sys.argv[1].strip()
    pasta_cache = Path(sys.argv[2])
    voz = sys.argv[3]
    player = sys.argv[4]

    if not texto:
        return 0

    arquivo_saida = gerar_nome_arquivo(pasta_cache)
    asyncio.run(gerar_audio(texto, arquivo_saida, voz))

    if arquivo_saida.exists():
        tocar_audio(player, arquivo_saida)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
