import catalogSnapshot from "../../frontend/src/generated/bioinformatics-catalog.json" with { type: "json" };

const CATALOG_PATHS = new Set(["/api/research-commerce", "/api/research_commerce"]);
const JSON_HEADERS = {
  "Content-Type": "application/json; charset=utf-8",
  "Cache-Control": "no-store",
  "X-Content-Type-Options": "nosniff",
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: JSON_HEADERS });
}

function backendOrigin(env, incomingHost) {
  // Explicit opt-in; never route private requests to an arbitrary third-party host.
  if (!env.BACKEND_ORIGIN) return null;
  try {
    const value = new URL(env.BACKEND_ORIGIN);
    if (value.protocol !== "https:" || value.username || value.password ||
        value.search || value.hash || value.pathname !== "/" ||
        value.hostname !== "nigerflora-biosciences.vercel.app" ||
        value.hostname === incomingHost) return null;
    return value;
  } catch {
    return null;
  }
}

async function proxyApi(request, origin) {
  const incoming = new URL(request.url);
  const target = new URL(incoming.pathname + incoming.search, origin);
  const headers = new Headers(request.headers);
  headers.set("Accept", "application/json");
  headers.delete("host");
  const upstreamRequest = new Request(target, {
    method: request.method,
    headers,
    body: request.method === "GET" || request.method === "HEAD" ? null : request.body,
    redirect: "manual",
  });
  let response;
  try {
    response = await fetch(upstreamRequest, { redirect: "manual", signal: AbortSignal.timeout(10000) });
  } catch {
    return json({ detail: "The research service API is temporarily unavailable." }, 503);
  }
  if (response.status >= 300 && response.status < 400) {
    return json({ detail: "The API returned an unexpected redirect." }, 502);
  }
  const type = response.headers.get("content-type") || "";
  if (!type.toLowerCase().includes("application/json")) {
    return json({ detail: "The API returned non-JSON content. Check deployment routing." }, 502);
  }
  const responseHeaders = new Headers(response.headers);
  responseHeaders.set("Cache-Control", "no-store");
  responseHeaders.set("X-Content-Type-Options", "nosniff");
  return new Response(response.body, { status: response.status, headers: responseHeaders });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!url.pathname.startsWith("/api/")) {
      return env.ASSETS.fetch(request);
    }
    const origin = backendOrigin(env, url.hostname);
    if (CATALOG_PATHS.has(url.pathname) && request.method === "GET") {
      if (origin) {
        const response = await proxyApi(request, origin);
        if (response.ok) {
          try {
            const result = await response.json();
            if (Array.isArray(result.services) && result.services.length > 0 &&
                Array.isArray(result.addons) && typeof result.integrity_notice === "string") {
              return json({ ...result, catalog_mode: "live", checkout_available: true });
            }
          } catch {
            // The upstream catalog is malformed. Use a read-only snapshot.
          }
        }
      }
      return json(catalogSnapshot);
    }
    if (!origin) {
      return json({ detail: "Orders are unavailable until a verified backend is configured." }, 503);
    }
    return proxyApi(request, origin);
  },
};
