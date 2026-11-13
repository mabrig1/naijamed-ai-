import assert from "node:assert/strict";
import test from "node:test";
import { GET, HEAD, POST, PUT, PATCH, DELETE } from "../api/research-commerce.js";
import { readFileSync } from "node:fs";

const original = JSON.parse(readFileSync(new URL("../src/generated/bioinformatics-catalog.json", import.meta.url), "utf8"));

test("legacy frontend-root GET returns catalog JSON in read-only reference mode", async () => {
  const response = GET();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("Content-Type"), /^application\\/json/);
  assert.match(response.headers.get("Cache-Control"), /no-store/);
  const data = await response.json();
  assert.equal(data.catalog_mode, "reference");
  assert.equal(data.checkout_available, false);
  assert.equal(data.services.length, 7);
  assert.deepEqual(data.services, original.services);
  assert.ok(data.services.every(s => s.tiers?.length));
});

test("HEAD has no response body", async () => {
  const response = HEAD();
  assert.equal(response.status, 200);
  assert.equal(await response.text(), "");
});

for (const [method, action] of Object.entries({ POST, PUT, PATCH, DELETE })) {
  test("reject " + method + " without initiating transactions", async () => {
    const response = action();
    assert.equal(response.status, 503);
    assert.equal(response.headers.get("Allow"), "GET, HEAD");
    const error = await response.json();
    assert.match(error.detail, /Ordering is unavailable/);
  });
}
