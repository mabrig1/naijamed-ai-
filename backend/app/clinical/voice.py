from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import settings


def transcribe_audio(filename: str, data: bytes, mime_type: str, language_hint: str | None = None) -> dict[str, Any]:
    if len(data) > settings.CLINICAL_AUDIO_MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Audio exceeds upload limit")
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Voice transcription is not configured")

    prompt = (
        "Nigerian healthcare conversation. Preserve medication names exactly as spoken. "
        "The speaker may use Nigerian English, Pidgin, Igbo, Yoruba, or Hausa."
    )
    if language_hint:
        prompt += f" Language hint: {language_hint}."

    files = {"file": (filename or "audio.webm", data, mime_type or "application/octet-stream")}
    form = {"model": settings.OPENAI_TRANSCRIPTION_MODEL, "prompt": prompt, "response_format": "json"}
    headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
    try:
        response = httpx.post("https://api.openai.com/v1/audio/transcriptions", headers=headers, files=files, data=form, timeout=60)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Transcription provider error: {exc.response.status_code}")
    except httpx.RequestError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Transcription provider unavailable")
