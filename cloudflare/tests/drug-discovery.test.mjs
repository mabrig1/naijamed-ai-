import assert from "node:assert/strict";
import test from "node:test";
import { FREE_RESEARCH_MODELS, getDrugDiscoveryCatalog, handleDrugDiscovery } from "../src/drug-discovery.mjs";

const host = "https://nigerflora-preview.example.workers.dev";
const origin = new URL("https://nigerflora-biosciences.vercel.app");
const req = (path, init) => new Request(host + path, init);
const token = "Bearer signed.mock.test-token";
const payload = { task: "docking_result_interpretation", prompt: "Explain how to evaluate validated Vina docking output", consent_to_external_ai: true };

test("Drug-discovery catalog has exact free models and real scientific tools", async () => {
  assert.deepEqual(FREE_RESEARCH_MODELS, [
    "nvidia/nemotron-3-ultra-550b-a55b:free", "openrouter/free",
  ]);
  const res = await handleDrugDiscovery(req("/api/drug-discovery/models"), {}, null);
  assert.equal(res.status, 200);
  const data = await res.json();
  assert.equal(data.assistant.enabled, false);
  assert.equal(data.computational_engines.length, 4);
  assert.ok(data.computational_engines.every(x => x.live_worker_execution === false));
  assert.ok(!JSON.stringify(data).toLowerCase().includes("wan"));
});

test("AI remains disabled by default and never calls provider", async () => {
  const res = await handleDrugDiscovery(req("/api/drug-discovery/interpret", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  }), {}, origin);
  assert.equal(res.status, 503);
});

test("AI requires active verified researcher, not merely a bearer string", async (t) => {
  const prev = globalThis.fetch;
  t.after(() => { globalThis.fetch = prev; });
  globalThis.fetch = async () => new Response("No", { status: 401 });
  const res = await handleDrugDiscovery(req("/api/drug-discovery/interpret", {
    method: "POST", headers: { Authorization: token, "Content-Type": "application/json" }, body: JSON.stringify(payload),
  }), { RESEARCH_AI_ENABLED: "true", OPENROUTER_API_KEY: "test-key" }, origin);
  assert.equal(res.status, 401);
});

test("AI requires specific task and explicit consent to third-party provider", async (t) => {
  const prev = globalThis.fetch;
  t.after(() => { globalThis.fetch = prev; });
  globalThis.fetch = async (url) => {
    if (new URL(url).pathname === "/api/auth/me") return new Response(JSON.stringify({ id: "person" }), { status: 200, headers: { "Content-Type": "application/json" } });
    throw Error("AI endpoint should not be called without consent");
  };
  const res = await handleDrugDiscovery(req("/api/drug-discovery/interpret", {
    method: "POST", headers: { Authorization: token, "Content-Type": "application/json" },
    body: JSON.stringify({ task: "admet_methodology", prompt: "Review physicochemical descriptors" }),
  }), { RESEARCH_AI_ENABLED: "true", OPENROUTER_API_KEY: "test-key" }, origin);
  assert.equal(res.status, 400);
});

test("First preferred free model used when available", async (t) => {
  const prev = globalThis.fetch;
  t.after(() => { globalThis.fetch = prev; });
  const routed = [];
  globalThis.fetch = async (url, options) => {
    const path = new URL(url).pathname;
    if (path === "/api/auth/me") return new Response(JSON.stringify({ id: "person", is_active: true }), { status: 200, headers: { "Content-Type": "application/json" } });
    routed.push(JSON.parse(options.body).model);
    return new Response(JSON.stringify({ model: "nvidia/nemotron-3-ultra-550b-a55b:free", choices: [{ message: { content: "Use validated receptor and ligand structures, then assess RMSD and replicates." } }] }), {
      status: 200, headers: { "Content-Type": "application/json" },
    });
  };
  const res = await handleDrugDiscovery(req("/api/drug-discovery/interpret", {
    method: "POST", headers: { Authorization: token, "Content-Type": "application/json" }, body: JSON.stringify(payload),
  }), { RESEARCH_AI_ENABLED: "true", OPENROUTER_API_KEY: "test-key" }, origin);
  assert.equal(res.status, 200);
  const data = await res.json();
  assert.equal(data.computer_analysis_performed, false);
  assert.deepEqual(routed, ["nvidia/nemotron-3-ultra-550b-a55b:free"]);
  assert.ok(!JSON.stringify(data).includes("test-key"));
});

test("Free fallback only, and no paid model called if primary is unavailable", async (t) => {
  const prev = globalThis.fetch;
  t.after(() => { globalThis.fetch = prev; });
  const models = [];
  globalThis.fetch = async (url, options) => {
    if (new URL(url).pathname === "/api/auth/me") return new Response(JSON.stringify({ id: "person" }), { status: 200, headers: { "Content-Type": "application/json" } });
    const model = JSON.parse(options.body).model;
    models.push(model);
    if (models.length === 1) return new Response(JSON.stringify({ error: "Rate limited" }), { status: 429, headers: { "Content-Type": "application/json" } });
    return new Response(JSON.stringify({ model: "fallback-free", choices: [{ message: { content: "Interpret cautiously" } }] }), { status: 200, headers: { "Content-Type": "application/json" } });
  };
  const res = await handleDrugDiscovery(req("/api/drug-discovery/interpret", {
    method: "POST", headers: { Authorization: token, "Content-Type": "application/json" }, body: JSON.stringify(payload),
  }), { RESEARCH_AI_ENABLED: "true", OPENROUTER_API_KEY: "test-key" }, origin);
  assert.equal(res.status, 200);
  assert.deepEqual(models, FREE_RESEARCH_MODELS);
  assert.equal((await res.json()).free_model_only, true);
});

test("Returns 503 rather than switching to any paid provider", async (t) => {
  const prev = globalThis.fetch;
  t.after(() => { globalThis.fetch = prev; });
  let calls = 0;
  globalThis.fetch = async (url) => {
    if (new URL(url).pathname === "/api/auth/me") return new Response(JSON.stringify({ id: "person" }), { status: 200, headers: { "Content-Type": "application/json" } });
    calls += 1;
    return new Response("unavailable", { status: 503 });
  };
  const res = await handleDrugDiscovery(req("/api/drug-discovery/interpret", {
    method: "POST", headers: { Authorization: token, "Content-Type": "application/json" }, body: JSON.stringify(payload),
  }), { RESEARCH_AI_ENABLED: "true", OPENROUTER_API_KEY: "test-key" }, origin);
  assert.equal(res.status, 503);
  assert.equal(calls, 2);
});
