# API path aliases for Vercel Python functions (NigerFlora)

## Verified failure

On 13 November 2026, the authenticated owner opened
`/api/research-commerce` on the Preview URL and received FastAPI's
`{"detail":"Not Found"}` response. This shows a Python ASGI endpoint was
reachable, but its router did not match the incoming path.

The Vercel rewrite `source: /api/research-commerce` points to the file
`api/research_commerce.py`. The FastAPI function previously declared only
`/api/research_commerce`. Function routing and ASGI routing are two
independent stages: the internal file is selected but the ASGI app may still
see the hyphenated public URL.

Both paths are now explicitly registered on the same handler, for GET and
POST. The same treatment applies to research-studio, NcheSent bridge/analysis,
and the Paystack webhook handler, preserving signature verification.

## Verification

Run without secrets or external services:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p 'test_vercel_api_route_aliases.py' -v
```

On an authorized **new PR Preview** of this change, test:

```
https://<preview-host>/api/research-commerce
https://<preview-host>/bioinformatics-services
```

Expected for the first: HTTP 200 JSON with exactly 7 services.
For the second: all 7 packages visible. Do not treat a Vercel
Deployment Protection 401 or a Vercel Ready status as confirmation.
Review that order and payment actions remain safe; do not run real
charges during preview.

Do not promote/merge until verified. No environmental values, credentials,
payment settings, domain records, or production routing were changed.
