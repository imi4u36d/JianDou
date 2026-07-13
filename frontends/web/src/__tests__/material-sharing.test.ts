import { describe, expect, it, vi } from "vitest";
import { useMaterialSharing } from "@/composables/materials/useMaterialSharing";
import type { MaterialAssetLibraryItem } from "@/types";

function asset(): MaterialAssetLibraryItem {
  return {
    id: "asset-1",
    taskId: "task-1",
    stageType: "keyframe",
    clipIndex: 1,
    versionNo: 1,
    selectedForNext: false,
    mediaType: "image",
    title: "Frame",
    publicUrl: "/storage/frame.png",
    fileUrl: "/storage/frame.png",
    previewUrl: "/storage/frame.png",
    createdAt: "2026-07-11T00:00:00Z",
    updatedAt: "2026-07-11T00:00:00Z",
  };
}

describe("material sharing", () => {
  it("creates a public share and records it by asset", async () => {
    const dependencies = {
      createShare: vi.fn(async () => ({ shareId: "share-1" } as never)),
      deleteShare: vi.fn(async () => undefined as never),
      message: { success: vi.fn(), error: vi.fn() },
    };
    const sharing = useMaterialSharing(dependencies);
    sharing.openMaterialShareConfirm(asset());

    await sharing.acceptMaterialShareConfirm();

    expect(dependencies.createShare).toHaveBeenCalledWith({
      materialAssetId: "asset-1",
      sourceType: "task",
      sourceId: "task-1",
    });
    expect(sharing.sharedAssetRecords.value).toEqual({ "asset-1": "share-1" });
    expect(sharing.shareConfirmDialog.open).toBe(false);
  });

  it("removes an existing public share", async () => {
    const dependencies = {
      createShare: vi.fn(async () => ({ shareId: "share-1" } as never)),
      deleteShare: vi.fn(async () => undefined as never),
      message: { success: vi.fn(), error: vi.fn() },
    };
    const sharing = useMaterialSharing(dependencies);
    sharing.sharedAssetRecords.value = { "asset-1": "share-1" };
    sharing.openMaterialShareConfirm(asset());

    await sharing.acceptMaterialShareConfirm();

    expect(dependencies.deleteShare).toHaveBeenCalledWith("share-1");
    expect(sharing.sharedAssetRecords.value).toEqual({});
  });
});
