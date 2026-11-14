import assert from "node:assert/strict";
import test from "node:test";
import { handleResearchFiles } from "../src/research-files.mjs";

const origin = new URL("https://nigerflora-biosciences.vercel.app");
const base = "https://nigerflora-preview.example.workers.dev";
const auth = "Bearer valid.researcher.token";
const req = (path, init) => new Request(base + path, init);
const standardEnv = bucket => ({
  STORAGE_ENABLED: "true", R2_WRITES_ENABLED: "true",
  API_WRITES_ENABLED: "true", NIGERFLORA_R2: bucket,
});

function mockBucket() {
  const entries = new Map();
  return {
    entries,
    async list({ prefix, limit }) {
      const objects = [...entries.entries()].filter(([key]) => key.startsWith(prefix))
        .map(([key, val]) => ({ key, size: val.body.byteLength, customMetadata: val.customMetadata }));
      return { objects: objects.slice(0, limit), truncated: objects.length > limit };
    },
    async put(key, body, options) {
      entries.set(key, { body, customMetadata: options.customMetadata, httpMetadata: options.httpMetadata });
    },
    async get(key) {
      const x = entries.get(key);
      return x ? { ...x, body: new Response(x.body).body } : null;
    },
    async head(key) { return entries.get(key) || null; },
    async delete(key) { entries.delete(key); },
  };
}

function mockIdentity(t, role = "researcher") {
  const old = globalThis.fetch;
  t.after(() => { globalThis.fetch = old; });
  globalThis.fetch = async (url) => {
    if (new URL(url).pathname !== "/api/auth/me") throw Error("Unexpected request");
    return new Response(JSON.stringify({ id: "researcher_123", role, is_active: true }), {
      status: 200, headers: { "Content-Type": "application/json" },
    });
  };
}

test("R2 remains off with no binding", async () => {
  const res = await handleResearchFiles(req("/api/research-files"), {}, origin);
  assert.equal(res.status, 503);
});

test("No files disclosed without signed-in researcher", async () => {
  const bucket = mockBucket();
  const res = await handleResearchFiles(req("/api/research-files"), standardEnv(bucket), origin);
  assert.equal(res.status, 401);
  assert.equal(bucket.entries.size, 0);
});

test("An authenticated patient account cannot use research storage", async t => {
  mockIdentity(t, "patient");
  const res = await handleResearchFiles(req("/api/research-files", {
    headers: { Authorization: auth },
  }), standardEnv(mockBucket()), origin);
  assert.equal(res.status, 401);
});

test("Private R2 files are written, listed, downloaded and deleted by authenticated owner", async t => {
  mockIdentity(t);
  const bucket = mockBucket();
  const env = standardEnv(bucket);
  const saved = await handleResearchFiles(req("/api/research-files", {
    method: "POST",
    headers: { Authorization: auth, "Content-Type": "text/plain", "X-File-Name": "sample_notes.txt" },
    body: "research only",
  }), env, origin);
  assert.equal(saved.status, 201);
  const result = await saved.json();
  assert.ok(bucket.entries.has("researchers/researcher_123/" + result.id));
  const list = await handleResearchFiles(req("/api/research-files", {
    headers: { Authorization: auth },
  }), env, origin);
  const listed = await list.json();
  assert.equal(listed.files.length, 1);
  assert.equal(listed.files[0].name, "sample_notes.txt");
  const file = await handleResearchFiles(req("/api/research-files/" + result.id, {
    headers: { Authorization: auth },
  }), env, origin);
  assert.equal(file.status, 200);
  assert.equal(await file.text(), "research only");
  assert.match(file.headers.get("Content-Disposition"), /^attachment/);
  const removed = await handleResearchFiles(req("/api/research-files/" + result.id, {
    method: "DELETE", headers: { Authorization: auth },
  }), env, origin);
  assert.equal(removed.status, 200);
  assert.equal(bucket.entries.size, 0);
});

test("Separate storage-write and API-write gates prevent accidental uploads", async t => {
  mockIdentity(t);
  const bucket = mockBucket();
  const baseEnv = standardEnv(bucket);
  for (const env of [{ ...baseEnv, R2_WRITES_ENABLED: "false" }, { ...baseEnv, API_WRITES_ENABLED: "false" }]) {
    const res = await handleResearchFiles(req("/api/research-files", {
      method: "POST", headers: { Authorization: auth, "Content-Type": "text/plain" }, body: "test",
    }), env, origin);
    assert.equal(res.status, 503);
  }
  assert.equal(bucket.entries.size, 0);
});

test("Invalid ID, oversized file, and disallowed formats are rejected", async t => {
  mockIdentity(t);
  const env = standardEnv(mockBucket());
  const badId = await handleResearchFiles(req("/api/research-files/not-uuid", { headers: { Authorization: auth } }), env, origin);
  assert.equal(badId.status, 400);
  const dangerous = await handleResearchFiles(req("/api/research-files", {
    method: "POST", headers: { Authorization: auth, "Content-Type": "text/html" }, body: "<script>x</script>",
  }), env, origin);
  assert.equal(dangerous.status, 415);
  const oversized = await handleResearchFiles(req("/api/research-files", {
    method: "POST", headers: { Authorization: auth, "Content-Type": "text/plain",
      "Content-Length": String(12 * 1024 * 1024) }, body: "test",
  }), env, origin);
  assert.equal(oversized.status, 413);
});
