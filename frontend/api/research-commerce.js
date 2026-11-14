/**
 * Read-only emergency catalog for a legacy Vercel project rooted at "frontend".
 * In a correct repository-root deploy, Python API is authoritative.
 * No orders, payments, leads, auth or medical data are processed here.
 */
import catalog from "../src/generated/bioinformatics-catalog.json" with { type: "json" };

const HEADERS = {
  "Content-Type": "application/json; charset=utf-8",
  "Cache-Control": "no-store, max-age=0",
  "X-Content-Type-Options": "nosniff",
};

export function GET() {
  return new Response(JSON.stringify({
    ...catalog,
    catalog_mode: "reference",
    checkout_available: false,
  }), { status: 200, headers: HEADERS });
}

export function HEAD() {
  return new Response(null, { status: 200, headers: HEADERS });
}

function unavailable() {
  return new Response(JSON.stringify({
    detail: "Ordering is unavailable in catalog-only recovery mode. Restore the full FastAPI backend.",
  }), {
    status: 503,
    headers: { ...HEADERS, Allow: "GET, HEAD" },
  });
}

export const POST = unavailable;
export const PUT = unavailable;
export const PATCH = unavailable;
export const DELETE = unavailable;
