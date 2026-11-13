"""Minimal Gemini REST calls over httpx, without the heavy gRPC SDK.

Model URLs are constructed only from validated model identifiers, and the API
key is sent in a request header (never a query string). Clinical callers
retain their strict evidence-only / no-autonomous-diagnosis prompts.
"""
from __future__ import annotations

import base64
import math
import re
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import settings

_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models/"
_MODEL_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


def _model(value: str) -> str | None:
    name = str(value or "").removeprefix("models/")
    return name if _MODEL_RE.fullmatch(name) else None


def _call(model: str, method: str, body: dict[str, Any]) -> dict[str, Any] | None:
    key = settings.effective_gemini_key
    model_name = _model(model)
    if not key or not model_name or method not in {"generateContent", "embedContent"}:
        return None
    url = _API_BASE + quote(model_name, safe="") + ":" + method
    try:
        with httpx.Client(timeout=20, follow_redirects=False, trust_env=False) as client:
            response = client.post(
                url,
                json=body,
                headers={
                    "x-goog-api-key": key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        if response.status_code != 200 or len(response.content) > 262144:
            return None
        payload = response.json()
        return payload if isinstance(payload, dict) else None
    except (httpx.HTTPError, ValueError):
        return None


def generate_json_text(
    system: str,
    prompt: str,
    *,
    image: bytes | None = None,
    mime_type: str | None = None,
) -> str | None:
    parts: list[dict[str, Any]] = [{"text": prompt}]
    if image is not None:
        if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
            return None
        parts.append({
            "inline_data": {
                "mime_type": mime_type,
                "data": base64.b64encode(image).decode("ascii"),
            },
        })
    payload = _call(
        settings.CLINICAL_VISION_MODEL if image is not None else settings.CLINICAL_LLM_MODEL,
        "generateContent",
        {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseMimeType": "application/json"},
        },
    )
    if not payload:
        return None
    try:
        candidates = payload.get("candidates") or []
        content = candidates[0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in content if isinstance(p, dict))
        return text.strip() or None
    except (KeyError, IndexError, TypeError, AttributeError):
        return None


def embed_query(text: str) -> list[float] | None:
    model = _model(settings.GEMINI_EMBEDDING_MODEL)
    if not model:
        return None
    payload = _call(
        model,
        "embedContent",
        {
            "model": "models/" + model,
            "content": {"parts": [{"text": text}]},
            "taskType": "RETRIEVAL_QUERY",
        },
    )
    if not payload:
        return None
    values = (payload.get("embedding") or {}).get("values")
    if (
        not isinstance(values, list)
        or not values
        or not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in values)
    ):
        return None
    return [float(v) for v in values]
