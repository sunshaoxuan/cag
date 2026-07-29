import { describe, expect, it } from "vitest";

import { resolveApiBaseUrl } from "./api";

describe("One Agent Gateway API base URL", () => {
  it("uses the management console origin by default", () => {
    expect(resolveApiBaseUrl(undefined)).toBe("");
    expect(resolveApiBaseUrl("same-origin")).toBe("");
  });

  it("keeps an explicitly configured external Gateway", () => {
    expect(
      resolveApiBaseUrl(" http://gateway.example.test:8000/ "),
    ).toBe("http://gateway.example.test:8000");
  });
});
