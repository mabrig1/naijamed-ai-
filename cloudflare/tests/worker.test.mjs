import assert from "node:assert/strict";
import test from "node:test";
import worker from "../src/worker.mjs";

const base = "https://nigerflora-preview.example.workers.dev";
const offlineEnv = { ASSETS: { fetch: async () => new Response("asset") } };

test("public catalog always renders in read-only mode without backend", async () => {
  const res = await worker.fetch(new Request(base + "/api/research-commerce"), offlineEnv);
  const data = await res.json();
  assert.equal(res.status, 200);
  assert.equal(data.catalog_mode, "reference");
  assert.equal(data.checkout_available, false);
  assert.ok(data.services.length >= 7);
});

test("checkout fails closed without a backend", async () => {
  const res = await worker.fetch(new Request(base + "/api/research-commerce", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: '{"action":"create_order"}',
  }), offlineEnv);
  assert.equal(res.status, 503);
  assert.match(res.headers.get("content-type"), /json/);
});

test("malconfigured backend URL cannot receive an order", async () => {
  const res = await worker.fetch(new Request(base + "/api/research-commerce", {
    method: "POST", body: '{"action":"create_order"}',
  }), { ...offlineEnv, BACKEND_ORIGIN: "https://evil.example/" });
  assert.equal(res.status, 503);
});

test("SPA static assets stay separate from API paths", async () => {
  const res = await worker.fetch(new Request(base + "/bioinformatics-services"), offlineEnv);
  assert.equal(await res.text(), "asset");
});

test("upstream HTML fallback never masquerades as a catalog", async (t) => {
  const previous = globalThis.fetch;
  t.after(() => { globalThis.fetch = previous; });
  globalThis.fetch = async () => new Response("<html>SPA</html>", {
    status: 200, headers: { "Content-Type": "text/html" },
  });
  const res = await worker.fetch(new Request(base + "/api/research-commerce"), {
    ...offlineEnv, BACKEND_ORIGIN: "https://nigerflora-biosciences.vercel.app",
  });
  const data = await res.json();
  assert.equal(data.checkout_available, false);
  assert.equal(data.catalog_mode, "reference");
});

test("healthy upstream catalog permits verified checkout path", async (t) => {
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
  const res = await worker.fetch(new Request(base + "/api/research-commerce"), {
    ...offlineEnv, BACKEND_ORIGIN: "https://nigerflora-biosciences.vercel.app",
  });
  const data = await res.json();
  assert.equal(data.catalog_mode, "live");
  assert.equal(data.checkout_available, true);
  assert.equal(target, "https://nigerflora-biosciences.vercel.app/api/research-commerce");
});
