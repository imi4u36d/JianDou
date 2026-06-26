import { describe, expect, it } from "vitest";
import { publicShareAspectRatio, publicShareCardStyle, publicSharePreviewUrl } from "@/utils/public-shares";
import type { PublicShareItem } from "@/types";

function item(overrides: Partial<PublicShareItem>): PublicShareItem {
  return {
    id: "share_1",
    shareId: "share_1",
    materialAssetId: "asset_1",
    sourceType: "task",
    sourceId: "task_1",
    ownerUserId: 1,
    authorName: "user",
    title: "作品",
    mediaType: "image",
    publicUrl: "/storage/file.png",
    fileUrl: "/storage/file.png",
    previewUrl: "/storage/preview.png",
    likeCount: 0,
    likedByMe: false,
    sharedAt: "",
    updatedAt: "",
    status: "ACTIVE",
    ...overrides,
  };
}

describe("public share utilities", () => {
  it("keeps same-height cards proportional across common ratios", () => {
    expect(publicShareAspectRatio(item({ width: 1024, height: 1024 }))).toBe(1);
    expect(publicShareAspectRatio(item({ width: 1920, height: 1080 }))).toBeCloseTo(16 / 9);
    expect(publicShareAspectRatio(item({ width: 1080, height: 1920 }))).toBeCloseTo(9 / 16);
    expect(publicShareCardStyle(item({ width: 1920, height: 1080 }))).toEqual({ aspectRatio: "1.7778" });
  });

  it("chooses thumbnail and preview aliases only", () => {
    expect(publicSharePreviewUrl(item({ thumbnailUrl: "/storage/thumb.jpg" }))).toBe("/storage/thumb.jpg");
    expect(publicSharePreviewUrl(item({ thumbnailUrl: "", previewUrl: "/storage/preview.png" }))).toBe("/storage/preview.png");
    expect(publicSharePreviewUrl(item({ thumbnailUrl: "", previewUrl: "" }))).toBe("");
  });
});
