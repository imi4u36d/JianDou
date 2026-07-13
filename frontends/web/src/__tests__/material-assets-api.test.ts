import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  fetchMaterialAssetPage,
  fetchMaterialAssets,
  reuseMaterialAsset,
} from "@/api/material-assets";
import { getJson, postJson } from "@/api/client";

vi.mock("@/api/client", () => ({
  deleteJson: vi.fn(),
  getJson: vi.fn(),
  patchJson: vi.fn(),
  postForm: vi.fn(),
  postJson: vi.fn(),
}));

describe("material asset API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("preserves zero and false query values", () => {
    fetchMaterialAssetPage({
      q: "  hero  ",
      minRating: 0,
      clipIndex: 0,
      includeWorkflowArtifacts: false,
      offset: 0,
      limit: 20,
    });

    expect(getJson).toHaveBeenCalledWith(
      "/material-assets?q=hero&minRating=0&clipIndex=0&includeWorkflowArtifacts=false&offset=0&limit=20",
    );
  });

  it("normalizes paginated responses to a list", async () => {
    vi.mocked(getJson).mockResolvedValueOnce({
      items: [{ id: "asset-1" }],
      offset: 0,
      limit: 20,
      total: 1,
      hasMore: false,
      nextOffset: null,
    });

    await expect(fetchMaterialAssets()).resolves.toEqual([{ id: "asset-1" }]);
  });

  it("encodes asset identifiers when reusing material", () => {
    reuseMaterialAsset("asset/1");

    expect(postJson).toHaveBeenCalledWith(
      "/material-assets/asset%2F1/reuse",
      { mode: "clone" },
    );
  });
});
