from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import math
import re
from pathlib import Path

from core.caminhos import pasta_dados_app
from core.seguranca import carregar_json_seguro, salvar_json_seguro


PASTA_DOCS = pasta_dados_app() / "rag_docs"
ARQUIVO_INDEX = pasta_dados_app() / "rag_index.json"


@dataclass
class Chunk:
    text: str
    source: str
    chunk_id: str


def _padrao_index() -> dict:
    return {"version": 1, "chunks": [], "updated_at": ""}


def _tokenize(txt: str) -> list[str]:
    t = (txt or "").lower()
    t = re.sub(r"[^a-z0-9à-ÿ\s]", " ", t)
    toks = [w for w in t.split() if len(w) >= 2]
    return toks[:6000]


def _split_chunks(text: str, source: str, max_words: int = 140) -> list[Chunk]:
    words = text.split()
    out: list[Chunk] = []
    if not words:
        return out

    i = 0
    idx = 0
    while i < len(words):
        piece = " ".join(words[i : i + max_words]).strip()
        if piece:
            cid = hashlib.sha1(f"{source}:{idx}:{piece[:80]}".encode("utf-8")).hexdigest()[:16]
            out.append(Chunk(text=piece, source=source, chunk_id=cid))
        i += max_words
        idx += 1
    return out


def _read_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".log", ".csv", ".json"}:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader  # type: ignore

            reader = PdfReader(str(path))
            pages = []
            for p in reader.pages[:120]:
                pages.append(p.extract_text() or "")
            return "\n".join(pages)
        except Exception:
            return ""

    return ""


def reindexar_documentos(paths: list[str] | None = None) -> dict:
    PASTA_DOCS.mkdir(parents=True, exist_ok=True)
    arquivos: list[Path] = []

    if paths:
        for p in paths:
            pp = Path(p)
            if pp.is_file():
                arquivos.append(pp)
    else:
        for ext in ["*.txt", "*.md", "*.pdf", "*.log", "*.csv", "*.json"]:
            arquivos.extend(PASTA_DOCS.glob(ext))

    chunks: list[dict] = []
    for arq in arquivos:
        txt = _read_file(arq)
        if not txt.strip():
            continue
        for c in _split_chunks(txt, source=arq.name):
            chunks.append({"id": c.chunk_id, "source": c.source, "text": c.text})

    data = _padrao_index()
    data["chunks"] = chunks
    data["updated_at"] = datetime.now().isoformat(timespec="seconds")
    salvar_json_seguro(ARQUIVO_INDEX, data)

    return {
        "ok": True,
        "indexed_files": len(arquivos),
        "indexed_chunks": len(chunks),
        "docs_folder": str(PASTA_DOCS),
    }


def _load_index() -> dict:
    raw = carregar_json_seguro(ARQUIVO_INDEX, _padrao_index())
    if not isinstance(raw, dict):
        return _padrao_index()
    if not isinstance(raw.get("chunks"), list):
        raw["chunks"] = []
    return raw


def consultar_rag(pergunta: str, top_k: int = 3) -> dict:
    pergunta = (pergunta or "").strip()
    if len(pergunta) < 3:
        return {"ok": False, "error": "pergunta_curta"}

    idx = _load_index()
    chunks = idx.get("chunks", [])
    if not chunks:
        return {"ok": False, "error": "index_vazio"}

    q_tokens = _tokenize(pergunta)
    if not q_tokens:
        return {"ok": False, "error": "tokens_vazios"}

    scores: list[tuple[float, dict]] = []
    q_set = set(q_tokens)
    for c in chunks:
        if not isinstance(c, dict):
            continue
        txt = str(c.get("text", ""))
        if not txt:
            continue
        tks = _tokenize(txt)
        if not tks:
            continue
        overlap = len(q_set.intersection(set(tks)))
        if overlap <= 0:
            continue
        score = overlap / math.sqrt(len(tks) + 1)
        scores.append((score, c))

    if not scores:
        return {"ok": False, "error": "sem_match"}

    scores.sort(key=lambda x: x[0], reverse=True)
    top = [item for _, item in scores[: max(1, min(top_k, 6))]]

    fontes = sorted(set(str(i.get("source", "")) for i in top if i.get("source")))
    trechos = [str(i.get("text", "")).strip()[:280] for i in top]
    resumo = " ".join(trechos)

    return {
        "ok": True,
        "answer": resumo[:1200],
        "sources": fontes,
        "snippets": trechos,
    }
