# Caminhos de dados graváveis da NOVA.
# Centraliza arquivos que precisam ser persistidos pelo app.
from __future__ import annotations

from pathlib import Path


def pasta_dados_app():
    # Usa a pasta raiz do projeto para persistir memória e aprendizado.
    base = Path(__file__).resolve().parent.parent
    pasta = base / "data"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta
