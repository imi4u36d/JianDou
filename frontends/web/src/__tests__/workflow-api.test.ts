import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  deleteAllStageVersions,
  fetchWorkflowPage,
  startAutoPilot,
} from "@/api/workflows";
import { deleteJson, getJson, postJson } from "@/api/client";

vi.mock("@/api/client", () => ({
  deleteJson: vi.fn(),
  getJson: vi.fn(),
  patchJson: vi.fn(),
  postJson: vi.fn(),
}));

describe("workflow API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("serializes workflow filters consistently", () => {
    fetchWorkflowPage({
      q: "  opening scene  ",
      status: "all",
      sort: "updated_desc",
      offset: 0,
      limit: 25,
    });

    expect(getJson).toHaveBeenCalledWith(
      "/workflows?q=opening+scene&sort=updated_desc&offset=0&limit=25",
    );
  });

  it("encodes optional stage filters", () => {
    deleteAllStageVersions("workflow/1", "key frame");

    expect(deleteJson).toHaveBeenCalledWith(
      "/workflows/workflow%2F1/versions?stage_type=key+frame",
    );
  });

  it("encodes workflow identifiers for auto-pilot actions", () => {
    startAutoPilot("workflow/1");

    expect(postJson).toHaveBeenCalledWith(
      "/workflows/workflow%2F1/auto-pilot/start",
      {},
    );
  });
});
