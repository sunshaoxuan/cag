import { describe, expect, it } from "vitest";

import { createRequestId, resolveApiBaseUrl } from "./api";

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

describe("One Agent Gateway request identifiers", () => {
  it("creates an RFC 4122 version 4 identifier without randomUUID", () => {
    const cryptoWithoutRandomUuid = {
      getRandomValues<T extends ArrayBufferView | null>(array: T): T {
        if (array instanceof Uint8Array) {
          array.set([
            0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0xff, 0x77,
            0xff, 0x99, 0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff,
          ]);
        }
        return array;
      },
    } satisfies Pick<Crypto, "getRandomValues">;

    expect(createRequestId(cryptoWithoutRandomUuid)).toBe(
      "00112233-4455-4f77-bf99-aabbccddeeff",
    );
  });
});
