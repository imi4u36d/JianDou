import { ref } from "vue";
import { describe, expect, it, vi } from "vitest";
import { useMaterialPreview } from "@/composables/materials/useMaterialPreview";
import type { MaterialAssetLibraryItem } from "@/types";

function asset(id: string, mediaType: "image" | "video", title = id): MaterialAssetLibraryItem {
  return {
    id,
    title,
    mediaType,
    publicUrl: `/${id}.${mediaType === "video" ? "mp4" : "png"}`,
  } as MaterialAssetLibraryItem;
}

describe("material preview state", () => {
  it("maps media previews and navigates within loaded assets", async () => {
    const assets = ref([asset("image-1", "image"), asset("video-1", "video")]);
    const preview = useMaterialPreview({
      displayedAssets: assets,
      activeFavoriteFolderId: ref(""),
      hasMoreAssets: ref(false),
      loadMoreAssets: vi.fn(),
    });

    preview.openAssetPreview(assets.value[0]);
    expect(preview.previewDialog.kind).toBe("image");
    expect(preview.canPreviewPrevious.value).toBe(false);
    expect(preview.canPreviewNext.value).toBe(true);

    await preview.navigatePreview(1);
    expect(preview.previewAsset.value?.id).toBe("video-1");
    expect(preview.previewDialog.kind).toBe("video");
    expect(preview.canPreviewPrevious.value).toBe(true);
  });

  it("loads another page when navigating beyond the current tail", async () => {
    const assets = ref([asset("image-1", "image")]);
    const hasMoreAssets = ref(true);
    const loadMoreAssets = vi.fn(async () => {
      assets.value.push(asset("image-2", "image"));
      hasMoreAssets.value = false;
    });
    const preview = useMaterialPreview({
      displayedAssets: assets,
      activeFavoriteFolderId: ref(""),
      hasMoreAssets,
      loadMoreAssets,
    });
    preview.openAssetPreview(assets.value[0]);

    await preview.navigatePreview(1);

    expect(loadMoreAssets).toHaveBeenCalledOnce();
    expect(preview.previewAsset.value?.id).toBe("image-2");
  });

  it("keeps an open preview synchronized after an asset update", () => {
    const original = asset("image-1", "image", "旧名称");
    const preview = useMaterialPreview({
      displayedAssets: ref([original]),
      activeFavoriteFolderId: ref(""),
      hasMoreAssets: ref(false),
      loadMoreAssets: vi.fn(),
    });
    preview.openAssetPreview(original);

    preview.syncPreviewAsset(asset("image-1", "image", "新名称"));

    expect(preview.previewDialog.title).toBe("新名称");
  });
});
