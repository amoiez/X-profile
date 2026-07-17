import { describe, expect, it } from "vitest";

import { analyzeSchema } from "@/lib/validation";
import { compactNumber } from "@/lib/format";

describe("analyzeSchema", () => {
  it("strips @ and accepts a valid handle", () => {
    const r = analyzeSchema.parse({ username: "@Example_1", post_limit: 200 });
    expect(r.username).toBe("Example_1");
    expect(r.post_limit).toBe(200);
  });

  it("rejects invalid characters", () => {
    expect(() => analyzeSchema.parse({ username: "bad handle!", post_limit: 200 })).toThrow();
  });

  it("rejects too-long usernames", () => {
    expect(() =>
      analyzeSchema.parse({ username: "this_name_is_way_too_long", post_limit: 200 })
    ).toThrow();
  });

  it("rejects empty username", () => {
    expect(() => analyzeSchema.parse({ username: "", post_limit: 200 })).toThrow();
  });

  it("enforces post_limit bounds", () => {
    expect(() => analyzeSchema.parse({ username: "user", post_limit: 5 })).toThrow();
    expect(() => analyzeSchema.parse({ username: "user", post_limit: 9999 })).toThrow();
  });
});

describe("compactNumber", () => {
  it("formats large numbers compactly", () => {
    expect(compactNumber(1500)).toMatch(/1\.5K/i);
    expect(compactNumber(null)).toBe("—");
  });
});
