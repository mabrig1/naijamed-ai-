// Offline-first browser smoke test for the public NigerFlora services page.
// Run with: cd frontend && node tests/catalog-browser-smoke.mjs
// Requires a running Vite preview at http://127.0.0.1:4173.
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { chromium } from "playwright";

const snapshot = JSON.parse(await readFile(new URL("../src/generated/bioinformatics-catalog.json", import.meta.url), "utf8"));
const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
const page = await browser.newPage();
const root = process.env.PREVIEW_BASE_URL || "http://127.0.0.1:4173";
const api = "**/api/research-commerce";
let mode = "offline";

try {
  await page.route(api, async (route) => {
    if (route.request().method() !== "GET") {
      return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Not available" }) });
    }
    if (mode === "offline") {
      // Simulates the confirmed current production failure: HTTP 200 + HTML.
      return route.fulfill({ status: 200, contentType: "text/html", body: "<html>SPA fallback</html>" });
    }
    if (mode === "bad-json") {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ healthy: true }) });
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ...snapshot, catalog_mode: "live", checkout_available: true }),
    });
  });

  await page.goto(root + "/bioinformatics-services", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Retry connection" }).waitFor({ state: "visible" });
  await page.getByText("Live ordering is currently unavailable.", { exact: false }).waitFor({ state: "visible", timeout: 15000 });
  const offline = page.getByRole("button", { name: "Ordering temporarily unavailable" });
  assert.equal(await offline.count(), snapshot.services.length, "All seven packages must be visible without API JSON");
  for (const button of await offline.all()) {
    assert.equal(await button.isDisabled(), true, "No payment action in fallback mode");
  }
  assert.equal(await page.getByRole("heading", { name: snapshot.services[0].name }).count(), 1);
  console.log("PASS: HTML 200 fallback shows services with payment actions disabled");

  mode = "bad-json";
  await page.getByRole("button", { name: "Retry connection" }).click();
  await page.getByText("Live ordering is currently unavailable.", { exact: false }).waitFor({ state: "visible" });
  assert.equal(await page.getByRole("button", { name: "Ordering temporarily unavailable" }).count(), snapshot.services.length);
  console.log("PASS: malformed JSON cannot enable checkout");

  mode = "live";
  await page.getByRole("button", { name: "Retry connection" }).click();
  const enabled = page.getByRole("button", { name: "Get instant quote / order" });
  await enabled.first().waitFor({ state: "visible" });
  assert.equal(await enabled.count(), snapshot.services.length);
  assert.equal(await enabled.first().isEnabled(), true);
  assert.equal(await page.getByText("Live ordering is currently unavailable.", { exact: false }).count(), 0);
  console.log("PASS: valid live catalog clears error and enables order buttons");
} finally {
  await browser.close();
}
