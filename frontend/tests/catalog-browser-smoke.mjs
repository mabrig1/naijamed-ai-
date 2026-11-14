// Verifies a production-like React build for functionality-first service testing.
// Run from frontend with Vite preview on http://127.0.0.1:4173.
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { chromium } from "playwright";

const snapshot = JSON.parse(await readFile(new URL("../src/generated/bioinformatics-catalog.json", import.meta.url), "utf8"));
const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
const page = await browser.newPage({ acceptDownloads: true });
const root = process.env.PREVIEW_BASE_URL || "http://127.0.0.1:4173";
let mode = "offline";
let writes = 0;

try {
  await page.route("**/api/research-commerce", async route => {
    if (route.request().method() !== "GET") {
      writes += 1;
      return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Checkout disabled" }) });
    }
    if (mode === "offline") return route.fulfill({ status: 200, contentType: "text/html", body: "<html>SPA fallback</html>" });
    if (mode === "bad-json") return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ healthy: true }) });
    return route.fulfill({
      status: 200, contentType: "application/json",
      body: JSON.stringify({ ...snapshot, catalog_mode: "live", checkout_available: true }),
    });
  });
  await page.route("**/api/discovery", async route => {
    const data = route.request().postDataJSON();
    if (data.action !== "lookup_compound" && data.action !== "lookup_protein") {
      writes += 1;
      return route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "Authentication required" }) });
    }
    const asset = data.action === "lookup_compound"
      ? { kind: "compound", name: "Aspirin", external_id: "2244", molecular_formula: "C9H8O4", source: "PubChem", source_url: "https://pubchem.ncbi.nlm.nih.gov/compound/2244" }
      : { kind: "protein", name: "Crambin", external_id: "1CRN", source: "RCSB Protein Data Bank", source_url: "https://www.rcsb.org/structure/1CRN" };
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ result: asset, scientific_notice: "Research reference" }) });
  });

  await page.goto(root + "/bioinformatics-services", { waitUntil: "domcontentloaded" });
  await page.getByText("Reference catalog loaded;", { exact: false }).waitFor({ state: "visible" });
  const buttons = page.getByRole("button", { name: "Test this workflow" });
  assert.equal(await buttons.count(), snapshot.services.length, "Every service must offer a public test button");
  for (const button of await buttons.all()) assert.equal(await button.isEnabled(), true, "Testing never depends on checkout status");
  const text = await page.locator("body").innerText();
  assert.ok(!/₦|(?:\$\s*\d)|Paystack|Flutterwave|Ordering temporarily unavailable|Get instant quote/i.test(text), "No money or checkout language on public services");
  console.log("PASS: API returns HTML, but all seven test workflows remain accessible with no pricing");

  await buttons.first().click();
  await page.getByRole("button", { name: "Download test research brief" }).waitFor();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download test research brief" }).click();
  const file = await downloadPromise;
  assert.ok(file.suggestedFilename().endsWith("-test-brief.md"));
  console.log("PASS: research brief downloads without login, order, price or payment");

  mode = "bad-json";
  await page.getByRole("button", { name: "Check API again" }).click();
  await page.getByText("Reference catalog loaded;", { exact: false }).waitFor();
  assert.equal(await page.getByRole("button", { name: "Test this workflow" }).count(), snapshot.services.length);

  mode = "live";
  await page.getByRole("button", { name: "Check API again" }).click();
  await page.getByText("Live service metadata connected.", { exact: false }).waitFor();
  assert.equal(await page.getByRole("button", { name: "Test this workflow" }).count(), snapshot.services.length);
  console.log("PASS: valid catalog metadata changes status only, never enables checkout");

  await page.getByRole("button", { name: "Test this workflow" }).nth(1).click();
  await page.getByRole("button", { name: "Test compound lookup" }).click();
  await page.getByText("PubChem identity lookup completed.").waitFor();
  await page.getByText("Aspirin · CID 2244").waitFor();
  assert.equal(writes, 0, "No lead, account, order or payment endpoint should be called");
  console.log("PASS: public ADMET test retrieves real-shaped scientific references and never creates orders");
} finally {
  await browser.close();
}
