import { describe, expect, it } from "vitest";
import { normalizeNigerianPhone } from "../shared/medinaija-core";

describe("normalizeNigerianPhone", () => {
  it("normalizes 080 Nigerian format", () => {
    expect(normalizeNigerianPhone("0803 123 4567")).toBe("+2348031234567");
  });

  it("accepts international Nigerian format", () => {
    expect(normalizeNigerianPhone("+2348031234567")).toBe("+2348031234567");
  });

  it("rejects malformed numbers", () => {
    expect(() => normalizeNigerianPhone("123")).toThrow();
  });
});
