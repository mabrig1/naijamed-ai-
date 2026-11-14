import catalogSnapshot from "../../frontend/src/generated/bioinformatics-catalog.json" with { type: "json" };

// Production never changes from this preview configuration automatically.
// Every dynamic-capability flag must be explicitly enabled in Cloudflare.
const CATALOG_PATHS = new Set(["/api/research-commerce", "/api/research_commerce"]);
const COMMERCE_PATHS = new Set([
  ...CATALOG_PATHS,
  "/api/research-commerce/paystack-webhook",
  "/api/research_commerce/paystack_webhook",
  "/api/research_commerce_webhook",
]);
const JSON_HEADERS = {
  "Content-Type": "application/json; charset=utf-8",
  "Cache-Control": "no-store",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
};
const BACKEND_HOST = "nigerflora-biosciences.vercel.app";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: JSON_HEADERS });
}

function enabled(value) {
  return value === "true";
}

function backendOrigin(env, incomingHost) {
  // Absolute allowlist: never proxy to untrusted origins or to the Worker itself.
  if (!env.BACKEND_ORIGIN || !enabled(env.API_PROXY_ENABLED)) return null;
  try {
    const value = new URL(env.BACKEND_ORIGIN);
    if (value.protocol !== "https:" || value.username || value.password ||
        value.search || value.hash || value.pathname !== "/" || value.port ||
        value.hostname !== BACKEND_HOST || value.hostname === incomingHost) return null;
    return value;
  } catch {
    return null;
  }
}

function checkoutEnabled(env, origin) {
  // These three independent opt-ins must all be enabled to accept checkout
  // routes; a healthy-looking catalog is insufficient proof of payment safety.
  return Boolean(origin) && enabled(env.API_WRITES_ENABLED) && enabled(env.CHECKOUT_ENABLED);
}

async function proxyApi(request, origin) {
  const incoming = new URL(request.url);
  const target = new URL(incoming.pathname + incoming.search, origin);
  const headers = new Headers(request.headers);
  headers.set("Accept", "application/json");
  for (const key of [
    "host", "connection", "transfer-encoding", "proxy-authorization",
    "x-forwarded-host", "x-forwarded-proto", "x-forwarded-for",
  ]) headers.delete(key);
  const upstreamRequest = new Request(target, {
    method: request.method,
    headers,
    body: request.method === "GET" || request.method === "HEAD" ? null : request.body,
    redirect: "manual",
  });
  let response;
  try {
    response = await fetch(upstreamRequest, {
      redirect: "manual",
      signal: AbortSignal.timeout(10000),
    });
  } catch {
    return json({ detail: "The research API is temporarily unavailable." }, 503);
  }
  if (response.status >= 300 && response.status < 400) {
    return json({ detail: "The backend returned an unexpected redirect." }, 502);
  }
  if (response.status === 204) {
    return new Response(null, {
      status: 204,
      headers: { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" },
    });
  }
  const type = response.headers.get("content-type") || "";
  if (!type.toLowerCase().includes("application/json")) {
    return json({ detail: "The backend returned non-JSON content. Check API routing." }, 502);
  }
  const responseHeaders = new Headers(response.headers);
  responseHeaders.set("Cache-Control", "no-store");
  responseHeaders.set("X-Content-Type-Options", "nosniff");
  responseHeaders.set("Referrer-Policy", "no-referrer");
  return new Response(response.body, { status: response.status, headers: responseHeaders });
}

function readonlyCatalog() {
  return json({ ...catalogSnapshot, catalog_mode: "reference", checkout_available: false });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!url.pathname.startsWith("/api/")) {
      return env.ASSETS.fetch(request);
    }

    const origin = backendOrigin(env, url.hostname);
    const ordersEnabled = checkoutEnabled(env, origin);
    const writesEnabled = Boolean(origin) && enabled(env.API_WRITES_ENABLED);

    if (url.pathname === "/api/cloudflare-status") {
      if (request.method !== "GET" && request.method !== "HEAD") {
        return json({ detail: "Method not allowed." }, 405);
      }
      const result = json({
        service: "nigerflora-cloudflare-preview",
        mode: "preview",
        catalog_available: true,
        api_proxy_enabled: Boolean(origin),
        api_writes_enabled: writesEnabled,
        checkout_enabled: ordersEnabled,
      });
      return request.method === "HEAD"
        ? new Response(null, { status: 200, headers: result.headers })
        : result;
    }

    if (CATALOG_PATHS.has(url.pathname) && (request.method === "GET" || request.method === "HEAD")) {
      if (origin) {
        const upstream = await proxyApi(request, origin);
        if (upstream.ok && request.method === "GET") {
          try {
            const result = await upstream.json();
            if (Array.isArray(result.services) && result.services.length > 0 &&
                result.services.every(item => item && item.id &&
                  Array.isArray(item.tiers) && item.tiers.length > 0) &&
                Array.isArray(result.addons) &&
                typeof result.integrity_notice === "string" &&
                result.checkout_available !== false &&
                result.catalog_mode !== "reference") {
              return json({
                ...result,
                catalog_mode: ordersEnabled ? "live" : "reference",
                checkout_available: ordersEnabled,
              });
            }
          } catch {
            // Never enable ordering for a malformed upstream catalog.
          }
        }
      }
      return request.method === "HEAD"
        ? new Response(null, { status: 200, headers: JSON_HEADERS })
        : readonlyCatalog();
    }

    // No writes of any kind until the backend is verified AND explicitly
    // enabled; payment/order paths require an additional independent opt-in.
    if (request.method !== "GET" && request.method !== "HEAD" && !writesEnabled) {
      return json({ detail: "API write operations are disabled in preview mode." }, 503);
    }
    if (COMMERCE_PATHS.has(url.pathname) && !ordersEnabled) {
      return json({ detail: "Commerce and payment operations are disabled pending verification." }, 503);
    }
    if (!origin) {
      return json({ detail: "Live API proxy is disabled or unavailable; public catalog remains viewable." }, 503);
    }
    return proxyApi(request, origin);
  },
};
