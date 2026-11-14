import assert from "node:assert/strict";
import test from "node:test";
import worker from "../src/worker.mjs";

const base = "https://nigerflora-preview.example.workers.dev";
const backend = "https://nigerflora-biosciences.vercel.app";
const offlineEnv = { ASSETS: { fetch: async () => new Response("asset") } };
const readEnv = {
  ...offlineEnv,
  BACKEND_ORIGIN: backend,
  API_PROXY_ENABLED: "true",
  API_WRITES_ENABLED: "false",
  CHECKOUT_ENABLED: "false",
};
const allEnabled = { ...readEnv, API_WRITES_ENABLED: "true", CHECKOUT_ENABLED: "true" };

test("public catalog works in reference mode without backend", async () => {
  const res = await worker.fetch(new Request(base + "/api/research-commerce"), offlineEnv);
  const data = await res.json();
  assert.equal(res.status, 200);
  assert.equal(data.catalog_mode, "reference");
  assert.equal(data.checkout_available, false);
  assert.ok(data.services.length >= 7);
});

test("explicit status endpoint exposes flags, never secrets or the backend URL", async () => {
  const res = await worker.fetch(new Request(base + "/api/cloudflare-status"), readEnv);
  const status = await res.json();
  assert.equal(res.status, 200);
  assert.equal(status.api_proxy_enabled, true);
  assert.equal(status.api_writes_enabled, false);
  assert.equal(status.checkout_enabled, false);
  assert.ok(!JSON.stringify(status).includes(backend));
  assert.match(res.headers.get("Cache-Control"), /no-store/);
});

test("API write operations are denied by default", async () => {
  const res = await worker.fetch(new Request(base + "/api/research-commerce", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: '{"action":"create_order"}',
  }), offlineEnv);
  assert.equal(res.status, 503);
  assert.match(res.headers.get("content-type"), /json/);
});

test("API proxy alone never enables writes, payments, or catalog checkout", async () => {
  const res = await worker.fetch(new Request(base + "/api/auth/login", {
    method: "POST", body: "{}",
  }), readEnv);
  assert.equal(res.status, 503);
  const webhook = await worker.fetch(new Request(base + "/api/research-commerce/paystack-webhook", {
    method: "POST", body: "{}",
  }), readEnv);
  assert.equal(webhook.status, 503);
});

test("commerce cannot go live merely by enabling API writes", async () => {
  const env = { ...readEnv, API_WRITES_ENABLED: "true" };
  const res = await worker.fetch(new Request(base + "/api/research-commerce", {
    method: "POST", body: '{"action":"quote"}',
  }), env);
  assert.equal(res.status, 503);
  const webhook = await worker.fetch(new Request(base + "/api/research_commerce_webhook", {
    method: "POST", body: "{}",
  }), env);
  assert.equal(webhook.status, 503);
});

test("untrusted, loopback, or disguised backend cannot receive a request", async () => {
  for (const origin of [
    "https://evil.example", "http://nigerflora-biosciences.vercel.app",
    "https://nigerflora-biosciences.vercel.app.evil.example",
    "https://nigerflora-biosciences.vercel.app:8443",
    "https://user@nigerflora-biosciences.vercel.app",
    "https://nigerflora-biosciences.vercel.app/path",
  ]) {
    const res = await worker.fetch(new Request(base + "/api/auth/profile"), {
      ...allEnabled, BACKEND_ORIGIN: origin,
    });
    assert.equal(res.status, 503, origin);
  }
});

test("SPA static assets stay separate from API paths", async () => {
  const res = await worker.fetch(new Request(base + "/bioinformatics-services"), offlineEnv);
  assert.equal(await res.text(), "asset");
});

test("no backend can trick catalog into enabling checkout with HTML", async (t) => {
  const previous = globalThis.fetch;
  t.after(() => { globalThis.fetch = previous; });
  globalThis.fetch = async () => new Response("<html>SPA</html>", {
    status: 200, headers: { "Content-Type": "text/html" },
  });
  const res = await worker.fetch(new Request(base + "/api/research-commerce"), allEnabled);
  const data = await res.json();
  assert.equal(data.checkout_available, false);
  assert.equal(data.catalog_mode, "reference");
});

test("a healthy upstream catalog stays read-only until independent checkout gates pass", async (t) => {
  const previous = globalThis.fetch;
  t.after(() => { globalThis.fetch = previous; });
  let target;
  globalThis.fetch = async (req) => {
    target = new URL(req.url).toString();
    return new Response(JSON.stringify({
      services: [{ id: "demo", tiers: [{ id: "basic" }] }],
      addons: [], integrity_notice: "research only",
    }), { status: 200, headers: { "Content-Type": "application/json" } });
  };
  const preview = await worker.fetch(new Request(base + "/api/research-commerce"), readEnv);
  const safeCatalog = await preview.json();
  assert.equal(safeCatalog.catalog_mode, "reference");
  assert.equal(safeCatalog.checkout_available, false);
  assert.equal(target, backend + "/api/research-commerce");

  const live = await worker.fetch(new Request(base + "/api/research-commerce"), allEnabled);
  const validCatalog = await live.json();
  assert.equal(validCatalog.catalog_mode, "live");
  assert.equal(validCatalog.checkout_available, true);
});

test("backend reference catalog never becomes live even with flags enabled", async (t) => {
  const previous = globalThis.fetch;
  t.after(() => { globalThis.fetch = previous; });
  globalThis.fetch = async () => new Response(JSON.stringify({
    services: [{ id: "demo", tiers: [{ id: "basic" }] }],
    addons: [], integrity_notice: "research only",
    catalog_mode: "reference", checkout_available: false,
  }), { status: 200, headers: { "Content-Type": "application/json" } });
  const res = await worker.fetch(new Request(base + "/api/research-commerce"), allEnabled);
  const result = await res.json();
  assert.equal(result.checkout_available, false);
  assert.equal(result.catalog_mode, "reference");
});

test("healthy backend only receives write calls after all flags are enabled", async (t) => {
  const previous = globalThis.fetch;
  t.after(() => { globalThis.fetch = previous; });
  let method;
  globalThis.fetch = async req => {
    method = req.method;
    return new Response(JSON.stringify({ message: "accepted" }), {
      status: 200, headers: { "Content-Type": "application/json" },
    });
  };
  const res = await worker.fetch(new Request(base + "/api/research-commerce", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: '{"action":"quote"}',
  }), allEnabled);
  assert.equal(res.status, 200);
  assert.equal(method, "POST");
});

test("HEAD supports catalog and status without returning a body", async () => {
  for (const url of ["/api/research-commerce", "/api/cloudflare-status"]) {
    const res = await worker.fetch(new Request(base + url, { method: "HEAD" }), offlineEnv);
    assert.equal(res.status, 200);
    assert.equal(await res.text(), "");
  }
});
