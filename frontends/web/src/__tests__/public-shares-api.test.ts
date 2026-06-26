import { describe, expect, it, vi } from "vitest";
import { createPublicShare, deletePublicShare, fetchPublicShares, likePublicShare, unlikePublicShare } from "@/api/public-shares";
import { deleteJson, getJson, postJson } from "@/api/client";

vi.mock("@/api/client", () => ({
  getJson: vi.fn(),
  postJson: vi.fn(),
  deleteJson: vi.fn(),
}));

describe("public share API", () => {
  it("lists public shares with query parameters", () => {
    fetchPublicShares({ type: "image", offset: 10, limit: 20, sort: "latest" });

    expect(getJson).toHaveBeenCalledWith("/public-shares?type=image&offset=10&limit=20&sort=latest");
  });

  it("creates and deletes public shares", () => {
    const payload = { materialAssetId: "asset_1", sourceType: "task" as const, sourceId: "task_1" };

    createPublicShare(payload);
    deletePublicShare("share/1");

    expect(postJson).toHaveBeenCalledWith("/public-shares", payload);
    expect(deleteJson).toHaveBeenCalledWith("/public-shares/share%2F1");
  });

  it("likes and unlikes public shares", () => {
    likePublicShare("share_1");
    unlikePublicShare("share_1");

    expect(postJson).toHaveBeenCalledWith("/public-shares/share_1/like", {});
    expect(deleteJson).toHaveBeenCalledWith("/public-shares/share_1/like");
  });
});
