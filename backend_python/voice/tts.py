from __future__ import annotations


def speak_text(text: str) -> None:
    if not str(text or "").strip():
        return
    raise RuntimeError("TTS pipeline not configured yet. This module is ready for Phase 2 wiring.")
