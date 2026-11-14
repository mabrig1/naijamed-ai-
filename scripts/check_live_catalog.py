"""Read-only NigerFlora catalog probe. Never sends credentials or writes data."""
from __future__ import annotations
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

def check(url: str) -> tuple[bool, str]:
    if not url.startswith("https://"):
        return False, "Only HTTPS endpoints are allowed"
    request = Request(url, headers={"Accept": "application/json", "Cache-Control": "no-cache"})
    try:
        with urlopen(request, timeout=12) as response:
            status = response.status
            kind = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            final_url = response.url
            data = response.read(200_000)
    except HTTPError as exc:
        # A Vercel-protected preview is not a failing application endpoint.
        # Inspect only a small non-sensitive signature; never print cookies,
        # authorization headers or raw HTML from the failed request.
        if exc.code in (401, 403):
            try:
                marker = exc.read(4096).decode("utf-8", errors="ignore").lower()
            except (AttributeError, OSError, ValueError):
                marker = ""
            content_type = (exc.headers.get("Content-Type", "") if exc.headers else "").lower()
            if "text/html" in content_type and any(term in marker for term in (
                "authentication required",
                "vercel authentication",
                "deployment protection",
                "vercel security checkpoint",
            )):
                return False, (
                    f"HTTP {exc.code}: Vercel deployment protection appears to block "
                    "anonymous preview verification. API health is unverified."
                )
            return False, (
                f"HTTP {exc.code}: anonymous request rejected. Check preview deployment "
                "protection or API authorization; API health is unverified."
            )
        return False, f"HTTP {exc.code}: service endpoint not ready"
    except (URLError, TimeoutError, OSError) as exc:
        return False, f"Network error: {type(exc).__name__}"
    if final_url != url:
        return False, f"Unexpected redirect: {final_url}"
    if status != 200:
        return False, f"Unexpected HTTP {status}"
    if kind != "application/json":
        return False, f"Expected JSON; received {kind or 'no content type'} (likely SPA HTML fallback)"
    try:
        payload = json.loads(data)
    except (ValueError, UnicodeDecodeError):
        return False, "Invalid JSON"
    if not isinstance(payload, dict) or not isinstance(payload.get("services"), list) or not payload["services"]:
        return False, "Missing nonempty services array"
    if not all(isinstance(s, dict) and s.get("id") and isinstance(s.get("tiers"), list) and s["tiers"] for s in payload["services"]):
        return False, "Catalog contains invalid service entries"
    if payload.get("checkout_available") is False or payload.get("catalog_mode") == "reference":
        return False, "Read-only reference catalog is available, but the full order API is not verified"
    return True, f"Valid JSON catalog: {len(payload['services'])} services"

def main() -> int:
    urls = sys.argv[1:]
    if not urls:
        raise SystemExit("Provide one or more https:// API URLs")
    failures = 0
    for url in urls:
        ok, message = check(url)
        print(("PASS" if ok else "FAIL") + " " + url + " - " + message)
        failures += not ok
    return int(failures > 0)

if __name__ == "__main__":
    raise SystemExit(main())
