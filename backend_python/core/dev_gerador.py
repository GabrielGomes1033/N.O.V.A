from __future__ import annotations

from pathlib import Path
import re
from typing import Iterable


def raiz_projeto_nova(base_dir: str | Path | None = None) -> Path:
    if base_dir is not None:
        return Path(base_dir).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def pasta_projetos_gerados(base_dir: str | Path | None = None) -> Path:
    if base_dir is not None:
        pasta = Path(base_dir).expanduser().resolve()
    else:
        pasta = raiz_projeto_nova() / "projetos_gerados"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def nome_seguro(nome: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9 _-]+", "", str(nome or "")).strip().lower()
    base = base.replace("-", "_").replace(" ", "_")
    base = re.sub(r"_+", "_", base).strip("_")
    return base or "projeto_nova"


def criar_pasta(caminho: str | Path, base_dir: str | Path | None = None) -> Path:
    destino = pasta_projetos_gerados(base_dir) / Path(caminho)
    destino.mkdir(parents=True, exist_ok=True)
    return destino


def criar_arquivo(
    caminho: str | Path,
    conteudo: str,
    *,
    base_dir: str | Path | None = None,
    sobrescrever: bool = False,
) -> tuple[Path, bool]:
    destino = pasta_projetos_gerados(base_dir) / Path(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)

    if destino.exists() and not sobrescrever:
        return destino, False

    destino.write_text(str(conteudo), encoding="utf-8")
    return destino, True


def criar_estrutura(
    pasta: str,
    arquivos: dict[str, str],
    *,
    base_dir: str | Path | None = None,
    sobrescrever: bool = False,
) -> dict[str, object]:
    nome_pasta = nome_seguro(pasta)
    criar_pasta(nome_pasta, base_dir=base_dir)

    criados: list[str] = []
    preservados: list[str] = []
    for nome_arquivo, conteudo in arquivos.items():
        _, criado = criar_arquivo(
            Path(nome_pasta) / nome_arquivo,
            conteudo,
            base_dir=base_dir,
            sobrescrever=sobrescrever,
        )
        if criado:
            criados.append(nome_arquivo)
        else:
            preservados.append(nome_arquivo)

    return {
        "project_dir": pasta_projetos_gerados(base_dir) / nome_pasta,
        "project_name": nome_pasta,
        "created_files": criados,
        "preserved_files": preservados,
    }


def formatar_lista_arquivos(arquivos: Iterable[str]) -> str:
    itens = [str(item).strip() for item in arquivos if str(item).strip()]
    if not itens:
        return "nenhum"
    return ", ".join(itens)
