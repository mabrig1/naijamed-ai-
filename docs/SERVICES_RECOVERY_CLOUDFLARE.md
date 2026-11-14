# NigerFlora services recovery and Cloudflare preview

## Confirmed repository issue

The public services page previously waited indefinitely when GET /api/research-commerce
failed or returned the React SPA HTML instead of catalog JSON. It now ships a
**read-only snapshot** generated from api/research_commerce.py, with an explicit
service-health banner and a Retry button. The original FastAPI catalog remains
the source of truth. Orders, leads, quotes and payments remain disabled unless
the live API responds with a valid catalog.

Generate the snapshot after pricing changes:

    python scripts/export_public_catalog.py
    python scripts/export_public_catalog.py --check

## Vercel root deployment

Set the Vercel project Root Directory to repository root (not frontend).
The root vercel.json builds frontend/dist and includes Python functions.
Both root and frontend vercel.json now explicitly exclude /api/ and /assets/
from SPA fallbacks, so a missing API cannot impersonate a healthy JSON endpoint.

Before promotion, inspect production/preview deployment runtime and run:

    curl -i -H 'Accept: application/json' https://<preview>/api/research-commerce

Expected: HTTP 200, Content-Type application/json, services array.
If HTML, an authentication redirect, 404 or 500 is returned, investigate
Vercel Root Directory, function packaging/build logs, and rewrite order.
Do not assume GitHub CI success proves a live API is healthy.

## Cloudflare Worker preview only

Cloudflare Worker code/config live under cloudflare/. The preview Worker
hosts the built React SPA using Static Assets and runs the Worker first for
/api/*; it DOES NOT change DNS or expose a production custom domain.

The Worker uses the generated catalog as a public read-only fallback. By
default it returns HTTP 503 for orders and other private API requests.
A private backend can be opted in by setting BACKEND_ORIGIN to the **exact**
trusted Vercel backend origin (the Worker only accepts
https://nigerflora-biosciences.vercel.app). The Worker forwards API calls only
if that backend is configured. Bad API HTML/redirect responses yield JSON 502.
Its GET catalog route marks checkout_available=true only when the backend
returns a valid JSON catalog; otherwise it marks checkout_available=false.

The preview does not run FastAPI, MongoDB, Python scientific libraries,
Paystack or medical workloads inside Workers.

### Validate without deployment

    npm ci --prefix frontend
    npm run build --prefix frontend
    python scripts/export_public_catalog.py --check
    node --test cloudflare/tests/worker.test.mjs
    npx wrangler deploy --dry-run --config cloudflare/wrangler.jsonc

### Optional preview deployment (requires separate authorization)

    npx wrangler deploy --config cloudflare/wrangler.jsonc

Verify the workers.dev URL **privately** before exposing it; workers.dev is
publicly reachable and must not be treated as a private environment.
Never connect nigerflora.mabrigkorie.org or set a production Worker Route until
preview tests and a separate DNS cutover approval.

### Readiness gates before any cutover

1. Live /api/research-commerce returns proper JSON and a nonempty catalog.
2. Browser /bioinformatics-services renders, both when healthy and when down.
3. Bad API HTML does not enable ordering or persist an infinite spinner.
4. Authenticated create_order, my_orders and Paystack callback verification work.
5. MongoDB access, secret environments, medical data handling and callbacks
   are verified separately, without exposing tokens in logs or browser assets.
6. Rollback: retain current Vercel DNS/alias and previous Worker version;
   revert DNS/Worker Route if the production smoke tests fail.


## Protected Preview Verification

Vercel Preview Deployment Protection can return HTTP 401 before the FastAPI
route executes. The anonymous GitHub diagnostic is informational only and
does not treat that status as success or proof of an application error.

An owner can visit the Vercel Preview deployment while signed into the
authorized Vercel team, then open:

- `/api/research-commerce` — must show JSON with a nonempty `services` array
- `/bioinformatics-services` — must show all 7 services
- Reference/fallback mode must keep order/checkout buttons disabled

Keep preview protection enabled. Do not expose automation bypass cookies or
tokens in screenshots, GitHub logs, browser console, or chat. Do not enable
production payments until authenticated orders and provider callbacks
have been tested separately. A Vercel Ready status only confirms build completion.
