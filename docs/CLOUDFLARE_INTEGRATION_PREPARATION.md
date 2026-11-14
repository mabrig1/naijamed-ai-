# NigerFlora — Cloudflare Workers integration preparation

**Status: PREPARED, NOT DEPLOYED.** This PR does not change the public domain,
existing Vercel production, nameservers, MongoDB, payment credentials, or
medical data. A Workers preview, if later deployed, is publicly reachable on
workers.dev unless separate Cloudflare Access restrictions are configured.

## Chosen architecture

Cloudflare Workers Static Assets: React/Vite frontend and client-side routes.
Cloudflare Worker: /api/* proxy boundary and read-only public catalog fallback.
Verified backend: the EXISTING Vercel Python FastAPI + MongoDB + payment services.
Do not migrate Python scientific workloads, webhook handlers or medical records
into the Worker without a separate compatibility and security review.

Cloudflare SPA routing is configured with:
- assets.directory = ../frontend/dist
- assets.not_found_handling = single-page-application
- assets.run_worker_first = ["/api/*"]
- env.ASSETS binding for the frontend

The API origin is hard-allowlisted to
https://nigerflora-biosciences.vercel.app. The Worker rejects other destinations,
even if someone accidentally configures BACKEND_ORIGIN to a different URL.
Do not set BACKEND_ORIGIN to nigerflora.mabrigkorie.org after cutover: doing
so would create a circular Worker request.

## Deployment flags (all default OFF)

| Setting | Default | Meaning |
| --- | --- | --- |
| API_PROXY_ENABLED | false | Allows Worker to call the trusted Vercel backend |
| API_WRITES_ENABLED | false | Allows non-GET/HEAD API actions to go through |
| CHECKOUT_ENABLED | false | Extra gating for commerce, webhook and checkout |
| BACKEND_ORIGIN | unset | Must match the exact allowlisted HTTPS Vercel hostname |

Example no-secret Worker config has the three flags set to false. A live
catalog does NOT enable checkout unless all flags are explicitly true and
the backend returns a structurally valid JSON catalog.

GET /api/cloudflare-status returns only safe mode/flag booleans and never
reports the backend URL, credentials or patient data.

### Local preparation — no cloud credentials needed

Run from repository root:

    python scripts/export_public_catalog.py --check
    npm ci --prefix frontend --no-audit --no-fund
    npm run build --prefix frontend
    node --test cloudflare/tests/worker.test.mjs
    node --test cloudflare/tests/integration-config.test.mjs
    npx --yes wrangler@4.160.1 deploy --dry-run --config cloudflare/wrangler.jsonc

The dry-run must compile without deploying or assigning domains.

### Optional isolated Cloudflare preview (requires separate approval)

1. In your Cloudflare account, confirm you control the correct zone.
2. Keep the production site on Vercel. Do not add any Custom Domain or Route.
3. Connect a reviewed, scoped Cloudflare token; do not paste it in chat.
4. Explicitly approve deploying only the preview Worker before running:

       npx wrangler@4.160.1 deploy --config cloudflare/wrangler.jsonc

5. Start with all flags false and no BACKEND_ORIGIN.
6. Preview tests: GET /bioinformatics-services shows seven packages,
   GET /api/research-commerce returns JSON reference mode,
   GET /api/cloudflare-status shows checkout_enabled=false,
   POST /api/research-commerce returns HTTP 503.
7. Only after Vercel backend health is proven on an owner-authorized preview,
   independently enable API_PROXY_ENABLED and specify BACKEND_ORIGIN, then
   re-test. Keep writes and checkout OFF.
8. Test auth, profiles, uploads, order flows, webhook signatures and provider
   callback URLs with isolated TEST credentials. Document a rollback path.
   Only then consider staged changes to write/checkout flags and production.

A new workers.dev preview is public by default. Do not include real patient
data, production payments, secret environment values or clinical records in
test fixtures or URLs.

### Production release gate — separate owner approval required

Never attach the Worker to nigerflora.mabrigkorie.org until:
- The actual Vercel backend returns HTTP 200, application/json and
  nonempty services from the approved backend origin, NOT an SPA HTML page.
- Vercel Deployment Protection on Preview is understood; an anonymous 401
  is not proof of backend success nor proof of application failure.
- Auth, research studio endpoints, upload/download content types, websocket
  requirements, and security controls are verified through the Worker.
  This initial Worker intentionally accepts JSON backend responses; non-JSON
  downloads are NOT ready and must be handled separately before rollout.
- Paystack and Flutterwave webhook signatures, callback URLs and order
  idempotency are tested with their providers' sandbox/test setups.
- Rollback owners can revert Worker Route/Custom Domain and flip the three
  feature flags to false without depending on the broken API.
- DNS/zone ownership, caching, WAF and access policy are approved.

Cloudflare's guidance: Workers Static Assets + SPA routing use
run_worker_first for /api/*, while a Worker used as the origin should be
mapped using a Custom Domain rather than a route in front of an origin.
Route creation and custom-domain assignment are EXPLICITLY out of scope
for this preparation PR.

References:
- https://developers.cloudflare.com/workers/static-assets/
- https://developers.cloudflare.com/workers/static-assets/routing/single-page-application/
- https://developers.cloudflare.com/workers/configuration/routing/routes/
- https://developers.cloudflare.com/workers/configuration/environment-variables/
- https://developers.cloudflare.com/workers/configuration/secrets/
