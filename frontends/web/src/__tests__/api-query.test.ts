import { describe, expect, it } from "vitest";

import { buildQueryString, withQuery } from "@/api/query";

describe("buildQueryString", () => {
  it("trims strings and omits empty optional values", () => {
    expect(
      buildQueryString({
        q: "  storyboard  ",
        status: " ",
        missing: undefined,
        nullable: null,
      }),
    ).toBe("q=storyboard");
  });

  it("preserves numeric zero and boolean false", () => {
    expect(buildQueryString({ offset: 0, limit: 20, includeWorkflowArtifacts: false })).toBe(
      "offset=0&limit=20&includeWorkflowArtifacts=false",
    );
  });

  it("encodes query values through URLSearchParams", () => {
    expect(buildQueryString({ q: "角色 A/B" })).toBe("q=%E8%A7%92%E8%89%B2+A%2FB");
  });
});

describe("withQuery", () => {
  it("returns the original path when all values are omitted", () => {
    expect(withQuery("/tasks", { q: "", status: undefined })).toBe("/tasks");
  });

  it("appends serialized values to the path", () => {
    expect(withQuery("/tasks", { offset: 0, limit: 50 })).toBe("/tasks?offset=0&limit=50");
  });
});
