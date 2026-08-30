import json
from typing import Any

from fastapi import HTTPException, status

from app.core.config import settings


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def analyze_medical_image(data: bytes, mime_type: str, context: str | None = None) -> dict[str, Any]:
    if mime_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload a JPEG, PNG, or WebP image")
    if len(data) > settings.CLINICAL_UPLOAD_MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Clinical image exceeds upload limit")
    if not settings.effective_gemini_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Vision model is not configured")

    import google.generativeai as genai

    genai.configure(api_key=settings.effective_gemini_key)
    model = genai.GenerativeModel(settings.CLINICAL_VISION_MODEL)
    prompt = (
        "Analyze this healthcare image as decision support only. It may be a paper prescription, lab report, or skin image. "
        "Extract visible text and objective visual features only. Do not diagnose a skin condition, do not recommend or dose medication, "
        "and do not infer values that are not visible. Return strict JSON with keys: document_type, extracted_text, observations, "
        "red_flags_for_clinician_review, confidence_notes."
    )
    if context:
        prompt += f" Context supplied by user: {context[:500]}"
    response = model.generate_content([prompt, {"mime_type": mime_type, "data": data}])
    text = (response.text or "").strip().strip("`")
    if text.lower().startswith("json"):
        text = text[4:].strip()
    try:
        return json.loads(text)
    except Exception:
        return {"document_type": "unknown", "extracted_text": text, "observations": [], "red_flags_for_clinician_review": [], "confidence_notes": "Model returned non-JSON output; clinician verification required."}
