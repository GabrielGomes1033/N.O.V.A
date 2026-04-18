from __future__ import annotations

from pathlib import Path


def transcribe_audio(audio_path: str) -> str:
    path = Path(audio_path)
    if not path.is_file():
        raise FileNotFoundError(f"audio file not found: {path}")
    raise RuntimeError("STT pipeline not configured yet. This module is ready for Phase 2 wiring.")
