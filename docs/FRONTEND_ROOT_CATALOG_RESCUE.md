# Emergency read-only catalog for legacy frontend-root deployments

The correct NigerFlora Vercel Root Directory is the repository root, which
deploys Python APIs from /api/ using /vercel.json. An older configuration
used frontend and could return the SPA HTML for the catalog API.

frontend/api/research-commerce.js is a GET-only read-only compatibility
function available **only** if Vercel builds with Root Directory frontend.
It returns JSON from the exact generated service snapshot, marked
catalog_mode=reference and checkout_available=false.

POST, PUT, PATCH and DELETE all return HTTP 503. This is not an API for
payments, orders, customer intake, health data, authentication or quotes.

When deployment uses correct Root Directory repository root, this nested
compatibility function is not a public route; FastAPI handles the catalog
and order actions from the top-level api directory.

Offline check:

    node --test frontend/tests/frontend-root-catalog.test.mjs

This compatibility improvement does not mean production is fixed.
Verify live JSON in an authorized preview before any production release.
