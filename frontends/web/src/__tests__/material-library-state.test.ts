import { ref } from "vue";
import { describe, expect, it } from "vitest";
import { useMaterialLibraryState } from "@/composables/materials/useMaterialLibraryState";
import type { MaterialAssetLibraryItem, MaterialFavoriteFolder } from "@/types";

const asset = (
  id: string,
  mediaType: "image" | "video",
  assetType = "free",
): MaterialAssetLibraryItem =>
  ({ id, title: id, mediaType, assetType }) as unknown as MaterialAssetLibraryItem;

describe("material library state", () => {
  it("projects tabs and favorite folders from the same asset source", () => {
    const assets = ref([asset("image-1", "image"), asset("video-1", "video")]);
    const folders = ref<MaterialFavoriteFolder[]>([
      {
        id: "folder-1",
        name: "收藏",
        assetIds: ["video-1", "cached-1"],
        createdAt: "2026-07-11T00:00:00Z",
      },
    ]);
    const cache = ref<Record<string, MaterialAssetLibraryItem>>({
      "cached-1": asset("cached-1", "image"),
    });
    const state = useMaterialLibraryState({
      assets: () => assets.value,
      favoriteFolders: () => folders.value,
      favoriteAssetCache: () => cache.value,
    });

    state.selectLibraryTab("image");
    expect(state.displayedAssets.value.map((item) => item.id)).toEqual(["image-1"]);
    state.activeFavoriteFolderId.value = "folder-1";
    expect(state.displayedAssets.value.map((item) => item.id)).toEqual(["video-1", "cached-1"]);
  });

  it("builds normalized page queries and resets selection filters", () => {
    const state = useMaterialLibraryState({
      assets: () => [asset("image-1", "image")],
      favoriteFolders: () => [],
      favoriteAssetCache: () => ({}),
      pageLimit: 20,
    });
    Object.assign(state.filters, { q: " cat ", model: " model ", clipIndex: "2" });
    state.selectLibraryTab("workflow");

    expect(state.buildPageQuery(40)).toMatchObject({
      q: "cat",
      model: "model",
      clipIndex: 2,
      includeWorkflowArtifacts: true,
      offset: 40,
      limit: 20,
    });
    state.toggleAssetSelection("image-1");
    expect(state.isAssetChecked("image-1")).toBe(true);
    expect(state.resetFilters()).toBe(true);
    expect(state.activeLibraryTab.value).toBe("all");
  });
});
