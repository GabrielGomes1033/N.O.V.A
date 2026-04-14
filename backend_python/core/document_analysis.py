from __future__ import annotations

from datetime import datetime
import base64
import csv
import io
import json
import re
import zipfile
from typing import Any


LIMITE_BYTES = 6 * 1024 * 1024  # 6MB


def _extrair_texto_docx(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
        txt = re.sub(r"<[^>]+>", " ", xml)
        txt = re.sub(r"\s+", " ", txt).strip()
        return txt
    except Exception:
        return ""


def _extrair_texto_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(io.BytesIO(data))
        paginas = []
        for p in reader.pages[:150]:
            paginas.append(p.extract_text() or "")
        return "\n".join(paginas).strip()
    except Exception:
        return ""


def _extrair_texto(filename: str, data: bytes) -> str:
    name = (filename or "").lower().strip()
    if name.endswith((".txt", ".md", ".log")):
        return data.decode("utf-8", errors="ignore")
    if name.endswith(".json"):
        try:
            parsed = json.loads(data.decode("utf-8", errors="ignore"))
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        except Exception:
            return data.decode("utf-8", errors="ignore")
    if name.endswith(".csv"):
        try:
            text = data.decode("utf-8", errors="ignore")
            reader = csv.reader(io.StringIO(text))
            rows = []
            for idx, row in enumerate(reader):
                if idx > 300:
                    break
                rows.append(" | ".join(row))
            return "\n".join(rows)
        except Exception:
            return data.decode("utf-8", errors="ignore")
    if name.endswith(".docx"):
        return _extrair_texto_docx(data)
    if name.endswith(".pdf"):
        return _extrair_texto_pdf(data)
    return data.decode("utf-8", errors="ignore")


def _normalizar_tokens(texto: str) -> list[str]:
    t = (texto or "").lower()
    t = re.sub(r"[^a-z0-9à-ÿ\s]", " ", t)
    toks = [w for w in t.split() if len(w) >= 3]
    return toks


def _resumo_executivo(texto: str, max_chars: int = 1200) -> str:
    linhas = [x.strip() for x in re.split(r"[\n\r]+", texto) if x.strip()]
    if not linhas:
        return ""
    bloco = " ".join(linhas)
    sentencas = re.split(r"(?<=[.!?])\s+", bloco)
    resumo = " ".join(sentencas[:6]).strip()
    if len(resumo) > max_chars:
        resumo = resumo[:max_chars].rsplit(" ", 1)[0] + "..."
    return resumo


def _top_palavras(texto: str, topn: int = 12) -> list[dict[str, Any]]:
    stop = {
        "para",
        "com",
        "que",
        "uma",
        "como",
        "não",
        "mais",
        "dos",
        "das",
        "nos",
        "nas",
        "por",
        "seu",
        "sua",
        "sobre",
        "este",
        "esta",
        "isso",
        "essa",
    }
    freq: dict[str, int] = {}
    for tok in _normalizar_tokens(texto):
        if tok in stop:
            continue
        freq[tok] = freq.get(tok, 0) + 1
    ordered = sorted(freq.items(), key=lambda kv: kv[1], reverse=True)[:topn]
    return [{"token": k, "count": v} for k, v in ordered]


def _detectar_riscos(texto: str) -> list[str]:
    t = texto.lower()
    riscos: list[str] = []
    checks = [
        ("senha", "Documento menciona senhas/credenciais."),
        ("token", "Documento menciona tokens/chaves de acesso."),
        ("cpf", "Documento pode conter dado pessoal sensível (CPF)."),
        ("cartão", "Documento pode conter dado financeiro sensível."),
        ("pix", "Documento inclui referência a transação financeira."),
        ("confidencial", "Documento marcado como confidencial."),
    ]
    for k, msg in checks:
        if k in t:
            riscos.append(msg)
    return riscos


def _slugify(nome: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9._-]", "_", (nome or "").strip())
    return base.strip("._-")[:80] or "documento"


def _aprender_automaticamente(filename: str, texto: str, resumo: str) -> dict[str, Any]:
    try:
        from core.rag_local import PASTA_DOCS, reindexar_documentos
        from core.aprendizado_admin import salvar_aprendizado
        from core.memoria_assuntos import aprender_assuntos
    except Exception as exc:
        return {"ok": False, "error": f"imports_failed: {exc}"}

    nome_limpo = _slugify(filename)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    arq_txt = PASTA_DOCS / f"auto_{nome_limpo}_{stamp}.txt"
    try:
        PASTA_DOCS.mkdir(parents=True, exist_ok=True)
        arq_txt.write_text(texto, encoding="utf-8")
    except Exception as exc:
        return {"ok": False, "error": f"save_failed: {exc}"}

    knowledge_added = 0
    try:
        if resumo.strip():
            salvar_aprendizado(
                f"resumo do arquivo {filename}",
                resumo.strip(),
                categoria="documento",
            )
            knowledge_added += 1
            salvar_aprendizado(
                f"o que tem no arquivo {filename}",
                resumo.strip(),
                categoria="documento",
            )
            knowledge_added += 1
    except Exception:
        pass

    assunto_out = {"ok": False, "updated": 0, "subjects": []}
    try:
        assunto_out = aprender_assuntos(
            texto=texto,
            origem=f"document:{filename}",
            resumo=resumo,
        )
    except Exception:
        pass

    try:
        idx = reindexar_documentos()
    except Exception as exc:
        return {
            "ok": False,
            "error": f"reindex_failed: {exc}",
            "saved_text_file": str(arq_txt),
            "knowledge_entries_added": knowledge_added,
        }

    return {
        "ok": True,
        "saved_text_file": str(arq_txt),
        "knowledge_entries_added": knowledge_added,
        "subject_memory": assunto_out,
        "rag_indexed_files": int(idx.get("indexed_files", 0)),
        "rag_indexed_chunks": int(idx.get("indexed_chunks", 0)),
    }


def analisar_documento_base64(
    filename: str,
    content_b64: str,
    auto_learn: bool = True,
) -> dict[str, Any]:
    fname = (filename or "").strip() or "documento"
    raw = (content_b64 or "").strip()
    if not raw:
        return {"ok": False, "error": "content_required"}
    try:
        data = base64.b64decode(raw, validate=False)
    except Exception:
        return {"ok": False, "error": "content_invalid_base64"}
    if not data:
        return {"ok": False, "error": "content_empty"}
    if len(data) > LIMITE_BYTES:
        return {"ok": False, "error": "content_too_large", "max_bytes": LIMITE_BYTES}

    texto = _extrair_texto(fname, data)
    texto = re.sub(r"\s+", " ", texto).strip()
    if len(texto) < 20:
        return {"ok": False, "error": "text_extraction_failed"}

    palavras = texto.split()
    top = _top_palavras(texto, topn=14)
    riscos = _detectar_riscos(texto)
    resumo = _resumo_executivo(texto)
    exemplos = []
    for part in re.split(r"(?<=[.!?])\s+", texto):
        p = part.strip()
        if len(p) >= 40:
            exemplos.append(p[:280])
        if len(exemplos) >= 4:
            break

    relatorio = {
        "ok": True,
        "report": {
            "file_name": fname,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "stats": {
                "bytes": len(data),
                "chars": len(texto),
                "words": len(palavras),
                "estimated_pages": max(1, round(len(palavras) / 450)),
            },
            "executive_summary": resumo,
            "keywords": top,
            "risks": riscos,
            "sample_excerpts": exemplos,
            "recommendations": [
                "Valide os pontos-chave com base no objetivo do documento.",
                "Remova ou masque credenciais/dados pessoais antes de compartilhar.",
                "Se necessário, peça um relatório focado (financeiro, técnico, jurídico).",
            ],
        },
    }
    if auto_learn:
        relatorio["learning"] = _aprender_automaticamente(fname, texto, resumo)
    else:
        relatorio["learning"] = {"ok": False, "skipped": True}
    return relatorio
