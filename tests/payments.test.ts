import crypto from "node:crypto";
import { describe, expect, it } from "vitest";
import { verifyPaystackSignature } from "../lib/paystack";

describe("verifyPaystackSignature", () => {
  it("accepts the matching sha512 HMAC", () => {
    const secret = "test_secret";
    const body = JSON.stringify({ event: "charge.success", data: { reference: "ref_1" } });
    const signature = crypto.createHmac("sha512", secret).update(body).digest("hex");
    expect(verifyPaystackSignature(body, signature, secret)).toBe(true);
  });

  it("rejects a forged signature", () => {
    expect(verifyPaystackSignature("{}", "bad", "secret")).toBe(false);
  });
});
