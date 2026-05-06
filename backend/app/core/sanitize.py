"""
Input sanitization helpers used by Pydantic validators across all schemas.

Rules enforced:
- Strip leading/trailing whitespace (Pydantic str_strip_whitespace handles most of this)
- Remove null bytes (common injection vector)
- Remove HTML/script tags via simple regex (defense-in-depth; no HTML is ever rendered)
- Enforce per-field max length so oversized payloads are rejected at the schema layer
"""
import re

_NULL_BYTES = re.compile(r"\x00")
_HTML_TAGS  = re.compile(r"<[^>]+>", re.IGNORECASE)


def sanitize(value: str, max_length: int = 5000) -> str:
    """Clean a string field: strip nulls, remove tags, truncate."""
    if not isinstance(value, str):
        return value
    value = _NULL_BYTES.sub("", value)
    value = _HTML_TAGS.sub("", value)
    if len(value) > max_length:
        raise ValueError(f"Input too long (max {max_length} characters)")
    return value


# Convenience wrappers with standard limits

def sanitize_short(v: str) -> str:
    """For names, titles — 500 chars."""
    return sanitize(v, 500)


def sanitize_medium(v: str) -> str:
    """For descriptions, summaries — 2000 chars."""
    return sanitize(v, 2000)


def sanitize_long(v: str) -> str:
    """For rich content, abstracts, findings — 10000 chars."""
    return sanitize(v, 10_000)
