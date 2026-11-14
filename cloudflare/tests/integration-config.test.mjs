import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";

const config = JSON.parse(readFileSync(new URL("../wrangler.jsonc", import.meta.url), "utf8"));

test("Cloudflare config is strictly preview-only and cannot capture custom domain", () => {
  assert.equal(config.name, "nigerflora-biosciences-preview");
  assert.equal(config.workers_dev, true);
  assert.equal("routes" in config, false);
  assert.equal("route" in config, false);
  assert.equal("custom_domain" in config, false);
  assert.equal("zone_id" in config, false);
  assert.equal("zone_name" in config, false);
});

test("Cloudflare serves Vite assets and runs Worker for API paths", () => {
  assert.equal(config.assets.binding, "ASSETS");
  assert.equal(config.assets.directory, "../frontend/dist");
  assert.equal(config.assets.not_found_handling, "single-page-application");
  assert.ok(config.assets.run_worker_first.includes("/api/*"));
});

test("every feature gate starts disabled and no secrets or live URLs are bundled", () => {
  assert.deepEqual(config.vars, {
    API_PROXY_ENABLED: "false",
    API_WRITES_ENABLED: "false",
    CHECKOUT_ENABLED: "false",
    RESEARCH_AI_ENABLED: "false",
  });
  assert.ok(!("BACKEND_ORIGIN" in config.vars));
  assert.ok(!("secrets" in config));
});
