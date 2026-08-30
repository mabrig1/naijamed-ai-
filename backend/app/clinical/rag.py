from typing import Any

import httpx

from app.core.config import settings


def _embed_query(text: str) -> list[float] | None:
    if not settings.effective_gemini_key:
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.effective_gemini_key)
        result = genai.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL,
            content=text,
            task_type="retrieval_query",
        )
        return result.get("embedding")
    except Exception:
        return None


def retrieve_protocols(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Retrieve evidence chunks from a pre-indexed Qdrant collection.

    The collection should contain licensed/approved Nigerian STG, WHO, and locally
    reviewed protocol excerpts with payload fields: title, source, text, url, version.
    If the vector store is not configured, this deliberately returns no evidence
    rather than fabricating clinical guidance.
    """
    if not settings.QDRANT_URL or not settings.QDRANT_COLLECTION:
        return []
    vector = _embed_query(query)
    if not vector:
        return []

    headers = {"Content-Type": "application/json"}
    if settings.QDRANT_API_KEY:
        headers["api-key"] = settings.QDRANT_API_KEY
    url = f"{settings.QDRANT_URL.rstrip('/')}/collections/{settings.QDRANT_COLLECTION}/points/search"
    payload = {"vector": vector, "limit": limit, "with_payload": True, "score_threshold": settings.RAG_SCORE_THRESHOLD}
    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        rows = response.json().get("result", [])
    except Exception:
        return []

    evidence: list[dict[str, Any]] = []
    for row in rows:
        item = row.get("payload") or {}
        text = item.get("text")
        if not text:
            continue
        evidence.append(
            {
                "title": item.get("title", "Clinical protocol"),
                "source": item.get("source", "Configured clinical knowledge base"),
                "url": item.get("url"),
                "version": item.get("version"),
                "text": text[:1800],
                "score": row.get("score"),
            }
        )
    return evidence
